#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

import networkx as nx
import random
import math
from operator import mul

from multiprocessing import Pool
import multiprocessing as multi



class Placer():

    DATA_FLOW = {"left-right": lambda pos: Placer.__to_horizontal(pos),\
                 "right-left": lambda pos: Placer.__to_horizontal(pos, False),\
                 "bottom-top": lambda pos: Placer.__to_vertical(pos),\
                 "top-bottom": lambda pos: Placer.__to_vertical(pos, False),\
                 "horizontal": lambda pos: Placer.__to_horizontal(pos, \
                                            bool(random.randint(0, 1))),\
                 "vertical":   lambda pos: Placer.__to_vertical(pos, \
                                            bool(random.randint(0, 1))),\
                 "any":        lambda pos: Placer.__to_horizontal(pos, \
                                            bool(random.randint(0, 1))) \
                                            if  bool(random.randint(0, 1)) \
                                            else Placer.__to_vertical(pos, \
                                            bool(random.randint(0, 1)))}

    ORIGIN_COORDS = {"left-right": [(0.0, 0.5)],
                    "right-left": [(1.0, 0.5)],
                    "bottom-top": [(0.5, 0.0)],
                    "top-bottom": [(0.5, 1.0)],
                    "horizontal": [(0.0, 0.5), (1.0, 0.5)],
                    "vertical": [(0.5, 0.0), (0.5, 1.0)],
                    "any": [(0.0, 0.5), (1.0, 0.5), (0.5, 0.0), (0.5, 1.0)]
                 }

    def __init__(self, method, dir, iterations = 50, randomness = "Full"):
        """ Initializes this class

            Args:
                method (str)    : initial mapping method
                                    available methods are follows:
                                        1. graphviz (default)
                                        2. tsort
                                        3. random
                dir (str)       : data flow direction
                                    available values corresponds to the keys of the dict "DATA_FLOW"
                iterations (int): maximum iteration number for generating a node position.
                                  Default = 50
                randomness (str): randomness of rounding.
                                  if it is "Full", then the positions are rounded fully randomly.
                                  if is is "Partial", then partilly randomly.
        """

        self.__iterations = iterations
        self.__method = method
        self.__dir = dir
        if not randomness in ["Full", "Partial"]:
            raise ValueError("Invalid randomness type: " + randomness)
        else:
            self.__randomness = randomness

    @staticmethod
    def __to_vertical(pos, bottom2top = True):
        # make sink nodes upper side
        if bottom2top:
            pos = {v: (x, 1 - y) for v, (x, y) in pos.items()}

        # randomly flip x position
        if random.randint(0, 1) == 0:
            pos = {v: (1 - x, y) for v, (x, y) in pos.items()}

        return pos

    @staticmethod
    def __to_horizontal(pos, left2right = True):
        if left2right:
            # rotate by + 90 deg
            pos = {v: (1 - y, x) for v, (x, y) in pos.items()}
        else:
            # rotate by -90 deg
            pos = {v: (y, 1 - x) for v, (x, y) in pos.items()}

        # randomly flip y position
        if random.randint(0, 1) == 0:
            pos = {v: (x, 1 - y) for v, (x, y) in pos.items()}

        return pos

    def generate_init_mappings(self, dag, width, height, count, proc_num=multi.cpu_count()):
        """Returns multiple initial mappings.

            Args:
                dag (networkx DiGraph): data-flow-graph
                width (int): PE array width
                height (int): PE array height
                count (int): try count to generate mappings
                Optional:
                    proc_num (int): the number of process
                                    Default is equal to cpu count
            Returns:
                list: a list of mappings
        """
        if self.__method == "graphviz":
            mt_args = [(dag, random.randint(1, width), height) for i in range(count)]

            p = Pool(proc_num)
            results = p.map(self.mt_wrapper, mt_args)
            p.close()

            init_mapping = []
            init_hashable_mapping = set() # for checking dupulication
            for mapping in results:
                # remove invalid results
                if not mapping is None:
                    if not mapping.values() in init_hashable_mapping:
                        init_mapping.append(mapping)
                        init_hashable_mapping.add(mapping.values())

            return init_mapping

        elif self.__method == "tsort":
            return self.make_random_mappings(dag, width, height, count, 1)

        else:
            return self.make_random_mappings(dag, width, height, count, 0)

    def mt_wrapper(self, args):
        return self.make_graphviz_mapping(*args)


    def make_graphviz_mapping(self, dag, width, height):
        """ Makes nodes position on the PE array.

            Args:
                dag (networkx DiGraph): data-flow-graph
                width (int): PE array width
                height (int): PE array height

            Returns:
                Dictionary: keys are operation label, values are mapped positions of them.
                            In case of failure, returns None

        """

        # validate input dag
        if nx.is_directed_acyclic_graph(dag) == False:
            raise ValueError("Input data-flow-graph is not DAG")

        # check dag size
        node_num = len(dag.nodes())
        if node_num > width * height:
            return None

        # enumerate possible rectangles
        rect_pattern = [(w, h) for w in range(1, width + 1) for h in range(1, height + 1) if w * h >= node_num]

        # graph layout by dot's algorithm
        pos = nx.nx_pydot.graphviz_layout(dag, prog="dot")

        # normalize coordinates
        max_x = max([x for (x, y) in pos.values()])
        max_y = max([y for (x, y) in pos.values()])
        pos = {v: (x / max_x, y / max_y) for v, (x, y) in pos.items()}

        # adjust for the data flow direction
        pos = self.DATA_FLOW[self.__dir](pos)

        # choose a rectangle pattern
        (map_width, map_height) = rect_pattern[random.randint(0, len(rect_pattern) - 1)]

        # calculate actual coordinates
        pos = {v: ((map_width - 1) * x, (map_height - 1) * y) for v, (x, y) in pos.items()}

        # try to rounding the conrdinates
        best_mapping_lest = len(pos)
        for i in range(self.__iterations):
            mapping = {v: self.__coord_rouding((x, y)) for v, (x, y) in pos.items()}
            # check duplication
            duplicated_node_num = len(list(mapping.values())) -  len(set(mapping.values()))
            if duplicated_node_num == 0:
                # check dependency
                # if self.__if_keep_dependency(dag, mapping):
                #     break
                break
            elif duplicated_node_num < best_mapping_lest:
                best_mapping = mapping
                best_mapping_lest = duplicated_node_num
        else:

            # fail to rouding
            # get duplicated nodes
            duplicated_nodes = {coord: [v for v in best_mapping.keys() if best_mapping[v] == coord] \
                            for coord in set(best_mapping.values()) \
                            if list(best_mapping.values()).count(coord) > 1}

            # fix one of nodes which are mapped to same coord
            for coord in duplicated_nodes:
                duplicated_nodes[coord].pop(\
                        random.randint(0, len(duplicated_nodes[coord]) - 1))

            # sort in order of lest node count
            duplicated_nodes = dict(sorted(duplicated_nodes.items(), key=lambda x: - len(x[1])))

            # get free coordinates
            free_coords = [(x, y) for x in range(map_width) for y in range(map_height)\
                            if not (x, y) in best_mapping.values()]

            for coord, nodes in duplicated_nodes.items():
                for v in nodes:
                    dists = [math.sqrt((x - coord[0]) ** 2 + (y - coord[1]) ** 2) \
                                for (x, y) in free_coords]
                    nearest_pos = free_coords[dists.index(min(dists))]
                    free_coords.remove(nearest_pos)
                    best_mapping[v] = nearest_pos
            return best_mapping

        return mapping

    def make_random_mappings(self, dag, width, height, size, sort_prob = 0.5):
        """ Generate random mappings

            Args:
                dag (networkx DiGraph): data-flow-graph
                width (int): PE array width
                height (int): PE array height
                size (int): The number of mappings to be generated
                Option:
                    sort_prob (float): topological sort probability.

            Returns:
                list: generated mappings

        """

        # validate input dag
        if nx.is_directed_acyclic_graph(dag) == False:
            raise ValueError("Input data-flow-graph is not DAG")

        # check dag size
        node_num = len(dag.nodes())
        if node_num > width * height:
            return None

        # enumerate possible rectangles
        rect_pattern = [(w, h) for w in range(1, width + 1) for h in range(1, height + 1) if w * h >= node_num]

        rtn_list = []
        for i in range(size):
            if random.random() < sort_prob:
                topological_sort_enable = True
            else:
                topological_sort_enable = False

            (map_width, map_height) = rect_pattern[random.randint(0, len(rect_pattern) - 1)]

            positions = random.sample([(x, y) for x in range(map_width) for y in range(map_height)], node_num)

            if topological_sort_enable:
                norm_origin = random.choice(self.ORIGIN_COORDS[self.__dir])
                origin = tuple(map(mul, norm_origin, \
                                (map_width - 1, map_height - 1)))
                positions = sorted(positions, key=lambda x: \
                                    (x[0] - origin[0])**2 + (x[1] - origin[1]) ** 2)
                rtn_list.append({k: v for k, v in zip(list(nx.topological_sort(dag)), positions)})
            else:
                rtn_list.append({k: v for k, v in zip(dag.nodes(), positions)})

        return rtn_list


    @staticmethod
    def __if_keep_dependency(dag, mapping):
        """Check dependency between operations.

            Args:
                dag (networkx digraph): data-flow-graph to be mapped

            mapping (dict): operation mapping
                                keys: operation labels
                                values: PE coordinates where the nodes are mapped

        """
        valid = True
        for u, v in dag.edges():
            if mapping[u][1] > mapping[v][1]:
                valid = False
                break

        return valid

    def __coord_rouding(self, coord):
        """ Round a float value coordinate to a int value coordinate.

        Args:
            coord: a list-like coordinate

        Return:
            a tuple: rounded coordinate

        """
        if self.__randomness == "Full":
            # Either ceil or floor is used randomly
            x_ceil = random.randint(0, 1) == 0
            y_ceil = random.randint(0, 1) == 0
        elif self.__randomness == "Partial":
            # extract after the decimal points
            x_dec = coord[0] - int(coord[0])
            y_dec = coord[0] - int(coord[0])
            # decide ceil or floor depending on the decimal
            x_ceil = random.random() < x_dec
            y_ceil = random.random() < y_dec

        if x_ceil and y_ceil:
            return (math.ceil(coord[0]), math.ceil(coord[1]))
        elif x_ceil and not y_ceil:
            return (math.ceil(coord[0]), math.floor(coord[1]))
        elif not x_ceil and y_ceil:
            return (math.floor(coord[0]), math.ceil(coord[1]))
        else:
            return (math.floor(coord[0]), math.floor(coord[1]))
