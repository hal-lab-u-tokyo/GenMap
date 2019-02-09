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
            self.preg = [random.randint(0, 1) for i in range(preg_num)]
        else:
            self.preg = []
        # get network model
        self.routed_graph = CGRA.getNetwork()
        # initialize each variable
        self.routing_cost = 0
        self.valid = False
        self.satisfy = False

    def __eq__(self, other):
        return self.mapping == other.mapping and self.preg == other.preg

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

        # duplication
        if len(child1.mapping.values()) != len(set(child1.mapping.values())):
            child1.mapping = father.mapping
        else:
            # compaction
            child1.mapping_compaction()

        if len(child2.mapping.values()) != len(set(child2.mapping.values())):
            child2.mapping = mother.mapping
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

    @staticmethod
    def mutSet(ind):
        LSPB = 0.5
        if random.random() <= LSPB:
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
            mut_op = random.choice(list(ind.mapping.keys()))
            width, height = ind.model.getSize()
            new_coord = (random.randint(0, width - 1), random.randint(0, height - 1))
            while new_coord in ind.mapping.values():
                new_coord = (random.randint(0, width - 1), random.randint(0, height - 1))

            ind.mapping[mut_op] = new_coord

        ind.valid = False
        ind.routed_graph = ind.model.getNetwork()

        return ind,


