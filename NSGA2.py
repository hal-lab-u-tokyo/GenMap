from deap import tools
from deap import base
from deap import algorithms
from deap import creator
import multiprocessing

from Individual import Individual
from EvalBase import EvalBase
from RouterBase import RouterBase
from Placer import Placer

class NSGA2():

    def __init__(self):

        self.__toolbox = base.Toolbox()

    def setup(self, CGRA, app, router, eval_list, proc_num = multiprocessing.cpu_count()):
        for evl in eval_list:
            if not isinstance(evl, EvalBase):
                raise TypeError(type(evl).__name__ + "is not EvalBase class")

        if not isinstance(router, RouterBase):
            raise TypeError(type(router).__name__ + "is not RouterBase class")

        width, height = CGRA.getSize()

        comp_dfg = app.getCompSubGraph()

        placer = Placer(iterations = 200, randomness = "Full")

        init_maps = placer.generate_init_mappings(comp_dfg, width, height, count = 10)

        if len(init_maps) < 1:
            return False

        creator.create("Fitness", base.Fitness, weights=tuple([-1.0 if evl.isMinimize() else 1.0 for evl in eval_list]))
        creator.create("Individual", Individual, fitness=creator.Fitness)

        # self.__pool = multiprocessing.Pool(proc_num)
        # self.__toolbox.register("map", self.__pool.map)
        self.__toolbox.register("individual", creator.Individual, CGRA, init_maps)
        self.__toolbox.register("population", tools.initRepeat, list, self.__toolbox.individual)
        self.__toolbox.register("evaluate", self.__eval_objectives, eval_list, CGRA, app, router)
        self.__toolbox.register("mate", Individual.cxSet)
        self.__toolbox.register("mutate", Individual.mutSet)
        self.__toolbox.register("select", tools.selNSGA2)

        return True

    def __eval_objectives(self, eval_list, CGRA, app, router, individual):
        self.__doRouting(CGRA, app, router, individual)
        return [obj.eval(CGRA, individual) for obj in eval_list]

    def __doRouting(self, CGRA, app, router, individual):
        print("a")
        g = individual.routed_graph
        cost = 0
        cost += router.comp_routing(CGRA, app.getCompSubGraph(), individual.mapping, g)
        cost += router.const_routing(CGRA, app.getConstSubGraph(), individual.mapping, g)
        cost += router.input_routing(CGRA, app.getInputSubGraph(), individual.mapping, g)
        cost += router.output_routing(CGRA, app.getOutputSubGraph(), individual.mapping, g)
        individual.routing_cost = cost

    def runOptimization(self):
        pop = self.__toolbox.population(n=100)
        print(len(pop))
        fitnesses = list(self.__toolbox.map(self.__toolbox.evaluate, pop))

        print(fitnesses)