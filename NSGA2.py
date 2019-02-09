from deap import tools
from deap import base
from deap import algorithms
from deap import creator
import multiprocessing
import numpy
import copy
from time import time

from Individual import Individual
from EvalBase import EvalBase
from RouterBase import RouterBase
from Placer import Placer

class NSGA2():
    def __init__(self, config = None):
        """Constructor of the NSGA2 class.

            Optional args:
                config (XML Element): a configuration of optimization parameters

        """
        # initilize toolbox
        self.__toolbox = base.Toolbox()
        self.__params = {"NGEN": 20, "MAX_STALL": 100, "INIT_POP_SIZE": 300, \
                        "LAMBDA": 100, "MU": 45, "RNDMU": 4, "CXPB": 0.7,\
                        "MUTPB": 0.3, "MUTELPB": 0.5}
        self.__pop = []

        # check if hypervolume is available
        self.__hv_logging = True
        try:
            from pygmo.core import hypervolume
            self.hypervolume = hypervolume
        except ImportError:
            self.__hv_logging = False


    def __getstate__(self):
        # make this instance hashable for pickle (needed to use multiprocessing)
        return {"pool": self}


    def setup(self, CGRA, app, router, eval_list, proc_num = multiprocessing.cpu_count()):
        """Setup NSGA2 optimization

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): an application to be optimized
                router (RouterBase): a router in which a routing algorithm is implemented
                eval_list (list of EvalBase): objective functions of the optimization
                Option:
                    proc_num (int): the number of process
                                    Default is equal to cpu count

            Returns:
                bool: if the setup successes, return True, otherwise return False.

            Raises:
                TypeError: if arguments of router and eval_list are invalid instance, raise this exception.
        """

        # check instance
        for evl in eval_list:
            if not isinstance(evl, EvalBase):
                raise TypeError(type(evl).__name__ + "is not EvalBase class")

        if not isinstance(router, RouterBase):
            raise TypeError(type(router).__name__ + "is not RouterBase class")

        # initilize weights of network model
        router.set_default_weights(CGRA)

        # obtain CGRA size
        width, height = CGRA.getSize()

        # obrain computation DFG
        comp_dfg = app.getCompSubGraph()

        # generate initial placer
        placer = Placer(iterations = 400, randomness = "Full")

        # make initial mappings
        init_maps = placer.generate_init_mappings(comp_dfg, width, height, count = 200)

        # check if mapping initialization successed
        if len(init_maps) < 1:
            return False

        # instance setting used in NSGA2
        creator.create("Fitness", base.Fitness, weights=tuple([-1.0 if evl.isMinimize() else 1.0 for evl in eval_list]))
        creator.create("Individual", Individual, fitness=creator.Fitness)

        # setting multiprocessing
        self.__pool = multiprocessing.Pool(proc_num)
        self.__toolbox.register("map", self.__pool.map)

        # register each chromosome operation
        self.__toolbox.register("individual", creator.Individual, CGRA, init_maps)
        self.__toolbox.register("population", tools.initRepeat, list, self.__toolbox.individual)
        self.__toolbox.register("evaluate", self.eval_objectives, eval_list, CGRA, app, router)
        self.__toolbox.register("mate", Individual.cxSet)
        self.__toolbox.register("mutate", Individual.mutSet)
        self.__toolbox.register("select", tools.selNSGA2)

        # set statics method
        stats = tools.Statistics(key=lambda ind: ind.fitness.values)
        stats.register("avg", numpy.mean)
        stats.register("std", numpy.std)
        stats.register("min", numpy.min)
        stats.register("max", numpy.max)

        return True

    def eval_objectives(self, eval_list, CGRA, app, router, individual):
        # routing the mapping
        self.__doRouting(CGRA, app, router, individual)
        # evaluate each objectives
        return [obj.eval(CGRA, individual) for obj in eval_list], individual

    def __doRouting(self, CGRA, app, router, individual):
        # check if routing is necessary
        if individual.valid:
            return

        # get penalty routing cost
        penalty = router.get_penalty_cost()

        # get a graph which the application to be mapped
        g = individual.routed_graph
        cost = 0
        # comp routing
        cost += router.comp_routing(CGRA, app.getCompSubGraph(), individual.mapping, g)
        if cost > penalty:
            individual.routing_cost = cost + penalty
            return

        # const routing
        cost += router.const_routing(CGRA, app.getConstSubGraph(), individual.mapping, g)
        if cost > penalty:
            individual.routing_cost = cost + penalty
            return

        # input routing
        cost += router.input_routing(CGRA, app.getInputSubGraph(), individual.mapping, g)
        if cost > penalty:
            individual.routing_cost = cost + penalty
            return

        # output routing
        cost += router.output_routing(CGRA, app.getOutputSubGraph(), individual.mapping, g)

        if cost > penalty:
            individual.routing_cost = cost + penalty
        else:
            # obtain valid routing
            individual.routing_cost = cost
            # eliminate unnecessary nodes and edges
            router.clean_graph(g)
            individual.valid = True

    def algo_wrapper(self):
        return algorithms.varOr()

    def runOptimization(self):
        # hall of fame
        hof = tools.ParetoFront()

        # generate first population
        self.__pop = self.__toolbox.population(n=self.__params["INIT_POP_SIZE"])

        # evaluate the population
        fitnesses, self.__pop = (list(l) for l in zip(*self.__toolbox.map(self.__toolbox.evaluate, self.__pop)))
        for ind, fit in zip(self.__pop, fitnesses):
            ind.fitness.values = fit
        print(fitnesses)

        # start evolution
        gen_count = 0
        stall_count = 0
        prev_hof_num = 0
        hof_log = []

        # Repeat evolution
        while gen_count < self.__params["NGEN"] and stall_count < self.__params["MAX_STALL"]:
            gen_count = gen_count + 1
            print("generation:", gen_count)

            # make offspring
            offspring = algorithms.varOr(self.__pop, self.__toolbox, self.__params["LAMBDA"], \
                                         self.__params["CXPB"], self.__params["MUTPB"])

            # Evaluate the individuals of the offspring
            fitnesses, offspring = (list(l) for l in zip(*self.__toolbox.map(self.__toolbox.evaluate, offspring)))
            for ind, fit in zip(offspring, fitnesses):
                ind.fitness.values = fit
            print(fitnesses)

            # make next population
            self.__pop = self.__toolbox.select(self.__pop + offspring , self.__params["MU"])
            hof.update(self.__pop)

            # check if there is an improvement
            if len(hof) == prev_hof_num:
                stall_count += 1
            else:
                stall_count = 0
            prev_hof_num = len(hof)

            # logging hof
            hof_log.append(copy.deepcopy(hof))

            # Hypervolume evolution (if possible)
            if self.__hv_logging:
                fitness_hof_log = [[ind.fitness.values for ind in hof] for hof in hof_log]
                hv = self.hypervolume([fit for sublist in fitness_hof_log for fit in sublist])
                ref_point = hv.refpoint(offset=0.1)   # Define global reference point
                hypervolume_log = [self.hypervolume(fit).compute(ref_point) for fit in fitness_hof_log]

            # Adding random individuals to the population (attempt to avoid local optimum)
            rnd_ind = self.__toolbox.population(n=self.__params["RNDMU"])
            fitnesses, rnd_ind = (list(l) for l in zip(*self.__toolbox.map(self.__toolbox.evaluate, rnd_ind)))
            for ind, fit in zip(rnd_ind, fitnesses):
                ind.fitness.values = fit
            self.__pop += rnd_ind

            print(len(hof))

        self.__pool.close()
        self.__pool.join()

        return hof

