import random
import copy

class Individual():
    def __init__(self, CGRA, init_maps = None, preg_num = None):
        self.__model = CGRA
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

    def cxSet(self, other):
        child1 = Individual(self.__model)
        child2 = Individual(self.__model)

    def mutSet(self):
        pass
