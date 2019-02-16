import networkx as nx
import random
import math

from multiprocessing import Pool
import multiprocessing as multi


class Placer():

    def __init__(self, iterations = 50, randomness = "Full"):
        """ Initializes this class

            Args:
                iterations (int): maximum iteration number for generating a node position.
                                  Default = 50
                randomness (str): randomness of rounding.
                                  if it is "Full", then the positions are rounded fully randomly.
                                  if is is "Partial", then partilly randomly.
        """

        self.__iterations = iterations
        if not randomness in ["Full", "Partial"]:
            raise ValueError("Invalid randomness type: " + randomness)
        else:
            self.__randomness = randomness

    def generate_init_mappings(self, dag, width, height, count, proc_num=multi.cpu_count()):
        """Returns multiple initial mappings.

            Args:
                dga (networkx DiGraph): data-flow-graph
                width (int): PE array width
                height (int): PE array height
                count (int): try count to generate mappings
                Optional:
                    proc_num (int): the number of process
                                    Default is equal to cpu count
            Returns:
                list: a list of mappings
        """
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


    def mt_wrapper(self, args):
        return self.make_position(*args)

    def make_position(self, dag, width, height):
        """ Makes nodes position on the PE array.

            Args:
                dga (networkx DiGraph): data-flow-graph
                width (int): PE array width
                height (int): PE array height

            Returns:
                Dictionary: keys are nodes names, values are node positions of them.
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

        # make sink nodes upper side
        pos = {v: (x, 1 - y) for v, (x, y) in pos.items()}
        # randomly flip x position
        if random.randint(0, 1) == 0:
            pos = {v: (1 - x, y) for v, (x, y) in pos.items()}

        # choose a rectangle pattern
        (map_width, map_height) = rect_pattern[random.randint(0, len(rect_pattern) - 1)]

        # calculate actual coordinates
        pos = {v: ((map_width - 1) * x, (map_height - 1) * y) for v, (x, y) in pos.items()}

        # try to rounding the conrdinates
        for i in range(self.__iterations):
            mapping = {v: self.__coord_rouding((x, y)) for v, (x, y) in pos.items()}
            # check duplication
            if len(list(mapping.values())) == len(set(mapping.values())):
                # check dependency
                # if self.__if_keep_dependency(dag, mapping):
                #     break
                break
        else:
            return None

        return mapping

    @staticmethod
    def make_random_mappings(dag, width, height, size, sort_prob = 0.5):
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
                positions = sorted(positions, key=lambda x: x[0]**2 + x[1] ** 2)
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
                                keys: node name
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