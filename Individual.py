import random
import copy

class Individual():
    def __init__(self, CGRA, init_maps = None, preg_num = None):
        self.model = CGRA
        if not init_maps is None:
            self.mapping = copy.deepcopy(init_maps[random.randint(0, len(init_maps) - 1)])
        else:
            self.mapping = []
        if not preg_num is None:
            self.preg = [random.randint(0, 1) for i in range(preg_num)]
        else:
            self.preg = []
        self.routed_graph = CGRA.getNetwork()
        self.routing_cost = 0
        self.valid = False

    @staticmethod
    def cxSet(father, mother):
        child1 = copy.deepcopy(father)
        child2 = copy.deepcopy(mother)

        child1.routed_graph = father.model.getNetwork()
        child2.routed_graph = father.model.getNetwork()
        child1.valid = False
        child2.valid = False

        cx_point = random.randint(0, len(father.mapping) - 1)
        op_nodes = list(father.mapping.keys())

        # crossover operation mapping
        for idx in range(cx_point, len(op_nodes)):
            op = op_nodes[idx]
            if not mother.mapping[op] in father.mapping.values():
                child1.mapping[op] = mother.mapping[op]
            if not father.mapping[op] in mother.mapping.values():
                child2.mapping[op] = father.mapping[op]

        # crossover pipeline regs conf
        if len(father.preg) != 0:
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
            ind.mapping[swap_op1] = ind.mapping[swap_op2]
            ind.mapping[swap_op2] = ind.mapping[swap_op1]
            if len(ind.preg) > 1:
                swap_idx1, swap_idx2 = random.sample(range(len(ind.preg)), 2)
                ind.preg[swap_idx1] = ind.preg[swap_idx2]
                ind.preg[swap_idx2] = ind.preg[swap_idx1]
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
