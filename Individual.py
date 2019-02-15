import random
import copy

class Individual():
    def __init__(self, CGRA, init_maps = None, preg_num = None):
        """Constructor of Individual class.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                init_maps (mapping): initial mappings
                preg_num (int): the number of pipeline registers
                                If it is None, there is no pipeline structure.
        """
        self.model = CGRA
        if not init_maps is None:
            # choose a mapping
            self.mapping = copy.deepcopy(init_maps[random.randint(0, len(init_maps) - 1)])
        else:
            self.mapping = []
        if not preg_num is None:
            # generate preg configuration randomly
            self.preg = [random.randint(0, 1) == 0 for i in range(preg_num)]
        else:
            self.preg = []
        # get network model
        self.routed_graph = CGRA.getNetwork()
        # initialize each variable
        self.routing_cost = 0
        self.valid = False
        self.satisfy = False
        # user data
        self.__userData = {}

    def __eq__(self, other):
        return self.mapping == other.mapping and self.preg == other.preg

    def saveEvaluatedData(self, key, data):
        """Save any evaluated data.

            Args:
                key: dictionary key for save data
                data: save data
        """
        self.__userData[key] = data

    def getEvaluatedData(self, key):
        """Return saved data.

            Args:
                key: dictionary key for save data

            Returns:
                Saved data type: saved data (if exist, else return None)
        """
        if key in self.__userData.keys():
            return self.__userData[key]
        else:
            return None

    def mapping_compaction(self):
        """
        Shift the mapping as far as possible
        """
        min_x = min([x for (x, y) in self.mapping.values()])
        min_y = min([y for (x, y) in self.mapping.values()])

        if min_x > 0 or min_y > 0:
            for op, (x, y) in self.mapping.items():
                self.mapping[op] = (x - min_x, y - min_y)


    @staticmethod
    def cxSet(father, mother):
        """Crossover operation.

            Args:
                father, mother (Individual): a parent to generate their children.

            Returns:
                (Individual, Individual): two children of the parent.

        """
        # copy from parent
        child1 = copy.deepcopy(father)
        child2 = copy.deepcopy(mother)

        # initialize each variable
        child1.routed_graph = father.model.getNetwork()
        child2.routed_graph = father.model.getNetwork()
        child1.valid = False
        child2.valid = False

        # set crossover point
        cx_point = random.randint(0, len(father.mapping) - 1)

        # get operation node names as a list
        op_nodes = list(father.mapping.keys())

        # crossover operation mapping
        mother_former = [mother.mapping[op_nodes[i]] for i in range(cx_point)]
        father_former = [father.mapping[op_nodes[i]] for i in range(cx_point)]
        for idx in range(cx_point, len(op_nodes)):
            op = op_nodes[idx]
            if not mother.mapping[op] in father_former:
                child1.mapping[op] = mother.mapping[op]
            if not father.mapping[op] in mother_former:
                child2.mapping[op] = father.mapping[op]

        # check dupulication of child1's mapping
        if len(child1.mapping.values()) != len(set(child1.mapping.values())):
            # try to eliminate the duplicated nodes
            if child1.eliminate_duplication() == False:
                # if fail the elimination, restore the mapping from father
                child1.mapping = copy.deepcopy(father.mapping)
        else:
            # compaction
            child1.mapping_compaction()

        # check dupulication of child1's mapping
        if len(child2.mapping.values()) != len(set(child2.mapping.values())):
            # try to eliminate the duplicated nodes
            if child2.eliminate_duplication() == False:
                # if fail the elimination, restore the mapping from father
                child2.mapping = copy.deepcopy(mother.mapping)
        else:
            # compaction
            child2.mapping_compaction()

        # crossover pipeline regs if it has its configuration
        if len(father.preg) != 0:
            # set crossover point
            cx_point = random.randint(0, len(father.preg) - 1)
            for i in range(cx_point, len(father.preg)):
                child1.preg[i] = mother.preg[i]
                child2.preg[i] = father.preg[i]

        return child1, child2

    def eliminate_duplication(self):
        """Try to eliminate duplicated mapping nodes

            Args: None

            Returns:
                bool: If there is a duplication-free mapping, returns True.
                      Otherwise, returns False
        """
        # get duplicated nodes
        mapping_list = list(self.mapping.values())
        duplicated_nodes = {k: v for k, v in self.mapping.items() if mapping_list.count(v) > 1}
        # sort the nodes randomly
        keys = list(duplicated_nodes.keys())
        random.shuffle(keys)
        duplicated_nodes = {k: duplicated_nodes[k] for k in keys}

        new_mapping = copy.deepcopy(self.mapping)

        for op, coord in duplicated_nodes.items():
            if list(new_mapping.values()).count(coord) == 1:
                continue
            else:
                # move the node to neighbor PE
                x, y = coord
                bound_x, bound_y = self.model.getSize()
                if y + 1 < bound_y and not (x, y + 1) in new_mapping.values():
                    # move to upper
                    new_mapping[op] = (x, y + 1)
                elif y - 1 >= 0 and not (x, y - 1) in new_mapping.values():
                    # move to lower
                    new_mapping[op] = (x, y - 1)
                elif x - 1 >= 0 and not (x - 1, y) in new_mapping.values():
                    # move to left
                    new_mapping[op] = (x - 1, y)
                elif x < bound_x and not (x + 1, y) in new_mapping.values():
                    # move to right
                    new_mapping[op] = (x + 1, y)
                else:
                    # fail to move
                    return False

        # update the mapping
        self.mapping = new_mapping
        return True

    @staticmethod
    def mutSet(local_search_prob, ind):
        """Mutation operation.

            Args:
                local_search_prob (float): local search probability
                ind: An Individual instance to mutate

            Returns:
                Individual: mutated individual
        """
        if random.random() <= local_search_prob:
            # Local Search (Swapping)
            swap_op1, swap_op2 = random.sample(list(ind.mapping.keys()), 2)
            tmp = ind.mapping[swap_op1]
            ind.mapping[swap_op1] = ind.mapping[swap_op2]
            ind.mapping[swap_op2] = tmp
            if len(ind.preg) > 1:
                swap_idx1, swap_idx2 = random.sample(range(len(ind.preg)), 2)
                tmp = ind.preg[swap_idx1]
                ind.preg[swap_idx1] = ind.preg[swap_idx2]
                ind.preg[swap_idx2] = tmp
        else:
            # Global Search (Change the configuration)
            mut_op = random.choice(list(ind.mapping.keys()))
            width, height = ind.model.getSize()
            # get free coordinate
            new_coord = (random.randint(0, width - 1), random.randint(0, height - 1))
            while new_coord in ind.mapping.values():
                new_coord = (random.randint(0, width - 1), random.randint(0, height - 1))

            # update the coordinate
            ind.mapping[mut_op] = new_coord

            # preg config
            if len(ind.preg) != 0:
                preg_idx = random.randint(0, len(ind.preg) - 1)
                ind.preg[preg_idx] = not(preg_idx[preg_idx])

        # make it invaliad
        ind.valid = False
        # init graph
        ind.routed_graph = ind.model.getNetwork()

        return ind,


