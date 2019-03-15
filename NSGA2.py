from deap import tools
from deap import base
from deap import algorithms
from deap import creator
import multiprocessing
import numpy
import copy
from time import time
from tqdm import tqdm

from Individual import Individual
from EvalBase import EvalBase
from RouterBase import RouterBase
from Placer import Placer

class NSGA2():
    def __init__(self, config, logfile = None):
        """Constructor of the NSGA2 class.

            Args:
                config (XML Element): a configuration of optimization parameters
                Optional:
                    logfile (_io.TextIOWrapper): log file

        """
        # initilize toolbox
        self.__toolbox = base.Toolbox()

        # get parameters
        self.__params = {}
        for param in config.iter("parameter"):
            if "name" in param.attrib:
                if not param.text is None:
                    try:
                        value = int(param.text)
                    except ValueError:
                        try:
                            value = float(param.text)
                        except ValueError:
                            raise ValueError("Invalid parameter: " + param.text)
                    self.__params[param.attrib["name"]] = value
                else:
                    raise ValueError("missing parameter value for " + param.attrib["name"])
            else:
                raise ValueError("missing parameter name")

        self.pop = []
        self.__placer = None
        self.__random_pop_args = []

        # check if hypervolume is available
        self.__hv_logging = True
        try:
            from pygmo.core import hypervolume
            self.hypervolume = hypervolume
        except ImportError:
            self.__hv_logging = False

        # regist log gile
        self.__logfile = logfile

    def __getstate__(self):
        # make this instance hashable for pickle (needed to use multiprocessing)
        return {"pool": self}


    def setup(self, CGRA, app, sim_params, router, eval_list, \
                eval_args = None, proc_num = multiprocessing.cpu_count()):
        """Setup NSGA2 optimization

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): an application to be optimized
                router (RouterBase): a router in which a routing algorithm is implemented
                eval_list (list of EvalBase): objective functions of the optimization
                Option:
                    eval_args (list): list of kwargs(dict) for each evaluation.
                    proc_num (int): the number of process
                                    Default is equal to cpu count

            Returns:
                bool: if the setup successes, return True, otherwise return False.

            Raises:
                TypeError: if arguments of router and eval_list are invalid instance, raise this exception.
        """

        # check instance
        for evl in eval_list:
            if not issubclass(evl, EvalBase):
                raise TypeError(evl.__name__ + "is not EvalBase class")

        # check eval args
        if not eval_args is None:
            if len(eval_list) != len(eval_args):
                raise TypeError("Inconsistent between evaluation list and their args")
            for args in eval_args:
                if not isinstance(args, dict):
                    raise TypeError("eval_args must be list of dictionary")
        else:
            eval_args = [{} for evl in eval_list]

        # uni-objective optimization
        if len(eval_list) == 1:
            self.__hv_logging = False

        if not issubclass(router, RouterBase):
            raise TypeError(router.__name__ + "is not RouterBase class")

        # initilize weights of network model
        router.set_default_weights(CGRA)

        # obtain CGRA size
        width, height = CGRA.getSize()

        # obrain computation DFG
        comp_dfg = app.getCompSubGraph()

        # generate initial placer
        self.__placer = Placer(iterations = self.__params["Initial place iteration"], \
                                randomness = "Full")

        # make initial mappings
        init_maps = self.__placer.generate_init_mappings(comp_dfg, width, height, \
                                                        count = self.__params["Initial place count"])

        self.__random_pop_args = [comp_dfg, width, height, self.__params["Random place count"],\
                                    self.__params["Topological sort probability"]]

        # check pipeline structure
        self.__preg_num = CGRA.getPregNumber()
        self.__pipeline_enable = self.__preg_num > 0

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
        if self.__pipeline_enable > 0:
            self.__toolbox.register("individual", creator.Individual, CGRA, init_maps, self.__preg_num)
        else:
            self.__toolbox.register("individual", creator.Individual, CGRA, init_maps)
        self.__toolbox.register("population", tools.initRepeat, list, self.__toolbox.individual)
        self.__toolbox.register("random_individual", creator.Individual, CGRA)
        self.__toolbox.register("evaluate", self.eval_objectives, eval_list, eval_args, CGRA, app, sim_params, router)
        self.__toolbox.register("mate", Individual.cxSet)
        self.__toolbox.register("mutate", Individual.mutSet, 0.5)
        self.__toolbox.register("select", tools.selNSGA2)

        # set statics method
        self.stats = tools.Statistics(key=lambda ind: ind.fitness.values)
        self.stats.register("min", numpy.min, axis=0)
        self.stats.register("max", numpy.max, axis=0)

         # progress bar
        self.progress = tqdm(total=self.__params["Maximum generation"], dynamic_ncols=True)

        # status display
        self.status_disp = [tqdm(total = 0, dynamic_ncols=True, desc=eval_cls.name(), bar_format="{desc}: {postfix}")\
                            for eval_cls in eval_list]

        return True

    def random_population(self, n):
        """ Generate rondom mapping as a population.

            Args:
                n (int): the number of the population

            Returns:
                list: a mapping list

        """
        random_mappings = self.__placer.make_random_mappings(*self.__random_pop_args)
        return [self.__toolbox.random_individual(random_mappings, self.__preg_num) for i in range(n)]

    def eval_objectives(self, eval_list, eval_args, CGRA, app, sim_params, router, individual):
        """ Executes evaluation for each objective
        """
        # routing the mapping
        self.__doRouting(CGRA, app, router, individual)
        # evaluate each objectives
        return [eval_cls.eval(CGRA, app, sim_params, individual, **args) \
                for eval_cls, args in zip(eval_list, eval_args)], individual

    def __doRouting(self, CGRA, app, router, individual):
        """
            Execute routing
        """
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
        if CGRA.getPregNumber() > 0:
            cost += router.output_routing(CGRA, app.getOutputSubGraph(), \
                                            individual.mapping, g, individual.preg)
        else:
            cost += router.output_routing(CGRA, app.getOutputSubGraph(), individual.mapping, g)

        if cost > penalty:
            individual.routing_cost = cost + penalty
        else:
            # obtain valid routing
            individual.routing_cost = cost
            # eliminate unnecessary nodes and edges
            router.clean_graph(g)
            individual.valid = True


    def runOptimization(self):
        # hall of fame
        hof = tools.ParetoFront()

        self.progress.set_description("Initilizing")
        # generate first population
        self.pop = self.__toolbox.population(n=self.__params["Initial population size"])

        # evaluate the population
        fitnesses, self.pop = (list(l) for l in zip(*self.__toolbox.map(self.__toolbox.evaluate, self.pop)))
        for ind, fit in zip(self.pop, fitnesses):
            ind.fitness.values = fit

        # start evolution
        gen_count = 0
        stall_count = 0
        prev_hof_num = 0
        hof_log = []

        # Repeat evolution
        while gen_count < self.__params["Maximum generation"] and stall_count < self.__params["Maximum stall"]:
            # show generation count
            gen_count = gen_count + 1
            self.progress.set_description("Generation {0}".format(gen_count))
            if not self.__logfile is None:
                self.__logfile.write("Generation {0}\n".format(gen_count))

            # make offspring
            offspring = algorithms.varOr(self.pop, self.__toolbox, self.__params["Offspring size"], \
                                         self.__params["Crossover probability"],\
                                         self.__params["Mutation probability"])

            # Evaluate the individuals of the offspring
            fitnesses, offspring = (list(l) for l in zip(*self.__toolbox.map(self.__toolbox.evaluate, offspring)))
            for ind, fit in zip(offspring, fitnesses):
                ind.fitness.values = fit

            # make next population
            self.pop = self.__toolbox.select(self.pop + offspring , self.__params["Select size"])
            hof.update(self.pop)

            # check if there is an improvement
            if len(hof) == prev_hof_num:
                if set([ind.fitness.values for ind in hof]) == \
                    set([ind.fitness.values for ind in hof_log[-1]]):
                    # no fitness improvement
                    stall_count += 1
                else:
                    stall_count = 0
            else:
                stall_count = 0
            prev_hof_num = len(hof)

            # logging hof
            hof_log.append(copy.deepcopy(hof))

            # Adding random individuals to the population (attempt to avoid local optimum)
            rnd_ind = self.random_population(self.__params["Random population size"])
            fitnesses, rnd_ind = (list(l) for l in zip(*self.__toolbox.map(self.__toolbox.evaluate, rnd_ind)))
            for ind, fit in zip(rnd_ind, fitnesses):
                ind.fitness.values = fit
            self.pop += rnd_ind

            # update status
            self.progress.set_postfix(hof_len=len(hof), stall=stall_count)
            self.progress.update(1)
            stats = self.stats.compile(hof)
            for i in range(len(stats["min"])):
                self.status_disp[i].set_postfix(min=stats["min"][i], max=stats["max"][i])

            # logging
            if not self.__logfile is None:
                self.__logfile.write("\thof_len = {0} stall = {1}\n".format(len(hof), stall_count))
                for i in range(len(stats["min"])):
                    self.__logfile.write("\t{obj}: min = {min}, max = max{max}\n".format(\
                                            obj = self.status_disp[i].desc, min = stats["min"][i],\
                                            max=stats["max"][i]))

        self.__pool.close()
        self.__pool.join()
        if self.__params["Maximum generation"] > gen_count:
            self.progress.update(self.__params["Maximum generation"] - gen_count)
        self.progress.close()
        for disp in self.status_disp:
            disp.close()

        print("\n\nFinish optimization")

        # Hypervolume evolution (if possible)
        if self.__hv_logging:
            fitness_hof_log = [[ind.fitness.values for ind in hof] for hof in hof_log]
            hv = self.hypervolume([fit for sublist in fitness_hof_log for fit in sublist])
            ref_point = hv.refpoint(offset=0.1)   # Define global reference point
            hypervolume_log = [self.hypervolume(fit).compute(ref_point) for fit in fitness_hof_log]
            return hof, hypervolume_log
        else:
            return hof, None


