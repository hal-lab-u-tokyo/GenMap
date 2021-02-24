from EvalBase import EvalBase
from DataPathAnalysis import DataPathAnalysis
from SolverSetup import SolverSetup

import networkx as nx
import pulp
import numpy as np
import cvxpy as cp

import copy
import math
import time

PENALTY_COST = 1000
MIN_SW = 1.5 # lower limit of SE's switching count 


# setting up for pulp solver
try:
    ilp_solver = SolverSetup("ILP").getSolver()
except SolverSetup.SolverSetupError as e:
    print("Fail to setup ILP solver:", e)
    sys.exit()

# setting up for cvxpy solver
try:
    cp_solver = SolverSetup("CP").getSolver()
except SolverSetup.SolverSetupError as e:
    print("Fail to setup CP solver:", e)
    sys.exit()

isCpOpt = True
leakmodel = None
delaymodel = None

class ModelBase():
    def __init__(self, sim_params):
        self.__k_gamma = sim_params.getUserdata("delay_power_model")["k_gamma"]
        self.__vth0 = sim_params.getUserdata("delay_power_model")["vth0"]
        self.bbv_min = sim_params.getUserdata("delay_power_model")["bbv_min"]
        self.bbv_max = sim_params.getUserdata("delay_power_model")["bbv_max"]
        if "bbv_step" in sim_params.getUserdata("delay_power_model").keys():
            self.need_quantize = True
            self.quant_step = sim_params.getUserdata("delay_power_model")["bbv_step"]
            self.bias = 10 ** math.ceil(-math.log10(self.quant_step))
        else:
            self.need_quantize = False

    def vthreshold(self, bbv):
        return self.__vth0 - self.__k_gamma * bbv


class DelayModel(ModelBase):
    """ delay model based on alpha-power-raw
    """
    def __init__(self, sim_params):
        super().__init__(sim_params)
        self.weight = sim_params.getUserdata("delay_power_model")["weight"]
        self.alpha = sim_params.getUserdata("delay_power_model")["alpha"]


    def delayScale(self, vdd, bbv):
        return vdd * ((vdd - self.vthreshold(bbv)) ** (- self.alpha))

class LeakModel(ModelBase):
    """ Leakage power model
        For more details, please see
            Fujita, Yu, et al. "Power optimization considering the chip temperature of low power reconfigurable accelerator CMA-SOTB." 2015 Third International Symposium on Computing and Networking (CANDAR). IEEE, 2015.
    """
    def __init__(self, sim_params):
        super().__init__(sim_params)
        self.coeff_vb = sim_params.getUserdata("delay_power_model")["coeff_vb"]
        self.coeff_vdd = sim_params.getUserdata("delay_power_model")["coeff_vdd"]
        self.coeff_tmp = sim_params.getUserdata("delay_power_model")["coeff_tmp"]
        self.leak0 = sim_params.getUserdata("delay_power_model")["leak0"]

    def leackage(self, bbv, p0, \
                mult = lambda x, y: x * y, exp = lambda x : math.e ** x):
        return mult(exp(self.coeff_vb * bbv), p0)


class PowerEval(EvalBase):
    class DependencyError (Exception):
        pass

    def __init__(self):
        """This evaluation must be carried out after MapWidthEval evaluation
            if you want mapping duplication.
        """
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual, **info):
        """Return estimated power

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for some simulations
                individual (Individual): An individual to be evaluated
                Options:
                    duplicate_enable (bool): True if you need the mapped data-flow
                                                to be duplicated horizontally.

            Returns:
                float: evaluated power

            Saved evaluation results:
                body_bias: optimized body bias voltage
                dynamic_power: dynamic power consumption
                leakage_power: leackage power consumption
        """
        global isCpOpt, leakmodel, delaymodel
        if individual.isValid() == False:
            return PENALTY_COST

        # get body bias domain
        bb_domains = CGRA.getBBdomains()
        if len(bb_domains) != 0 and len(sim_params.bias_range) > 1:
            do_bb_opt = True
        else:
            do_bb_opt = False

        duplicate_enable = False
        if "duplicate_enable" in info.keys():
            if info["duplicate_enable"] is True:
             duplicate_enable = True
             # chech dependency
             if individual.getEvaluatedData("map_width") is None:
                raise PowerEval.DependencyError("PowerEval must be carried out after map width evaluation")
        if "convex_program" in info.keys() and isCpOpt:
            # first setup
            if leakmodel is None:
                try:
                    delaymodel = DelayModel(sim_params)
                    leakmodel = LeakModel(sim_params)
                except KeyError as e:
                    raise KeyError("Some parameters for delay, leak model such as {0} are missing".format(e))
                eval_leak = PowerEval.eval_leak_cp
        else:
            isCpOpt = False
            eval_leak = PowerEval.eval_leak_ilp

        leak_power = eval_leak(CGRA, app, sim_params, individual, do_bb_opt)
        dyn_energy = PowerEval.eval_glitch(CGRA, app, sim_params, individual, duplicate_enable)

        # get dynamic energy of pipeline regs
        if CGRA.getPregNumber() > 0:
            dyn_energy += sim_params.preg_dynamic_energy * sum(individual.preg)

        dyn_power = sim_params.calc_power(app.getClockPeriod(sim_params.getTimeUnit()), \
                                          dyn_energy)

        individual.saveEvaluatedData("dynamic_power", dyn_power)
        individual.saveEvaluatedData("leakage_power", leak_power)

        return dyn_power + leak_power


    @staticmethod
    def get_opcodes(CGRA, app, individual):
        """Gets opcodes for each used ALU.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                individual (Individual): an individual
            Returns:
                Dict: opcodes of used ALUs
                    keys (str): ALU name of routed graph
                    values (str): opcode of the ALU
        """
        mapping = individual.mapping
        graph = individual.routed_graph
        op_attr = nx.get_node_attributes(app.getCompSubGraph(), "op")
        opcodes = {CGRA.getNodeName("ALU", pos): op_attr[op_label] \
                     if op_label in op_attr.keys() else "CAT" \
                         for op_label, pos in mapping.items()}
        # for routing ALU
        for alu, flag in nx.get_node_attributes(graph, "route").items():
            if flag:
                opcodes[alu] = CGRA.getRoutingOpcode(alu)
        return opcodes

    @staticmethod
    def eval_leak_cp(CGRA, app, sim_params, individual, leak_optimize):
        """Evaluates leackage power consumption.
            If necessary, it will optimize body bias voltage assignments
                by using convex optimization programming.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for simulations
                individual (Individual): An individual to be evaluated
                leak_optimize (bool): True if you need body bias optimization.

            Returns:
                float: leakage power of whole PE array.
        """
        if leak_optimize:
            # obtain domains
            bb_domains = CGRA.getBBdomains()
            Ndom = len(bb_domains.keys())

            # mapping domain name to domain ID
            domkey2ID = {dom: i for dom, i in zip(bb_domains.keys(), range(Ndom))}

            # set zero bias leak
            Pleak = [0.0 for _ in range(Ndom)]
            for domain in bb_domains.keys():
                Pleak[domkey2ID[domain]] = \
                        leakmodel.leak0 * len(bb_domains[domain]["ALU"])

            # make delay table
            #  keys:   node name
            #  values: coeff of alpha-power-model
            opcodes = PowerEval.get_opcodes(CGRA, app, individual)
            delay_table = {node: delaymodel.weight[opcode] \
                            for node, opcode in opcodes.items()}

            # make domain table
            #    key: node name, value: domain ID
            domain_table = {}
            for node in individual.routed_graph.nodes():
                for domain in bb_domains.keys():
                    if node in bb_domains[domain]["ALU"] or \
                        node in bb_domains[domain]["SE"]:
                        domain_table[node] = domkey2ID[domain]

            # get maximum latency
            max_lat = app.getClockPeriod(sim_params.getTimeUnit())

            # obtain data path
            dpathes = DataPathAnalysis.get_data_path(CGRA, individual)
            path_count = len(dpathes)

            # make delay matrix
            # size (path count x # of domains)
            D = np.full((path_count, Ndom), 0.0)
            for i in range(path_count):
                dp = dpathes[i]
                for node in dp:
                    D[i][domain_table[node]] += delay_table[node] \
                        if CGRA.isALU(node) else delaymodel.weight["SE"]

            # constructs convex optimization problem
            Dreqvec = cp.Parameter(path_count, value = np.full(path_count, max_lat))
            if Ndom > 1:
                # problem variables (vector of bbv)
                bbv = cp.Variable(Ndom)
                # body bias effects
                effvec = delaymodel.delayScale(0.9, bbv)
                # delay and power table
                dtable = cp.Parameter((path_count, Ndom), value = D, nonneg=True)
                ptable = cp.Parameter(Ndom, value=Pleak, nonneg=True)
                # range of bbv
                lbound = cp.Parameter(Ndom, value = np.full(Ndom, leakmodel.bbv_min))
                ubound = cp.Parameter(Ndom, value = np.full(Ndom, leakmodel.bbv_max))
                constraints = [dtable @ effvec <= Dreqvec, \
                                bbv <= ubound, bbv >= lbound]
            else:
                # for single domain
                # problem variables (vector of bbv)
                bbv = cp.Variable()
                # body bias effects
                effvec = delaymodel.delayScale(0.9, bbv)
                # delay and power table
                dtable = cp.Parameter(path_count, value = D.reshape(path_count), \
                                 nonneg=True)
                ptable = cp.Parameter(value=Pleak[0], nonneg=True)
                # range of bbv
                lbound = cp.Parameter(value=leakmodel.bbv_min)
                ubound = cp.Parameter(value=leakmodel.bbv_max)
                constraints = [dtable * effvec <= Dreqvec, \
                                bbv <= ubound, bbv >= lbound]

            power = leakmodel.leackage(bbv, ptable, mult=cp.multiply, \
                                        exp=cp.exp)
            # create minimization problem
            prob = cp.Problem(cp.Minimize(cp.sum(power)), constraints)
            solve_fail = False

            # solve
            try:
                prob.solve(**cp_solver)
            except cp.SolverError as e:
                solve_fail = True

            # check status
            solve_fail |= prob.status in ["infeasible", "unbounded"]

            # get status
            if not solve_fail:
                # get optimal value
                leak_power = prob.value
                individual.saveEvaluatedData("before_round_leakage", leak_power)
                # statistics
                stats = prob.solver_stats
                # print("solve time", stats.solve_time)
                # print("iter", stats.num_iters)

                # get optimal bbv assignment
                opt_bbv = [v for v in bbv.value] if Ndom > 1 else [bbv.value]
                # voltage rouding
                if delaymodel.need_quantize:
                    opt_bbv = PowerEval.round_bbv(D, opt_bbv, max_lat)

                leak_power = 0.0
                for bbv, p in zip(opt_bbv, Pleak):
                    leak_power += leakmodel.leackage(bbv, p)

                individual.saveEvaluatedData("body_bias", \
                    {domain: opt_bbv[domkey2ID[domain]] \
                        for domain in bb_domains.keys()})

            else:
                # fails to solve
                leak_power = PENALTY_COST
                individual.saveEvaluatedData("body_bias", {})
                individual.invalidate()

        else:
            width, height = CGRA.getSize()
            leak_power = leakmodel.leak0 * width * height

        return leak_power

    @staticmethod
    def round_bbv(delay_table, bbv_vec, max_lat):
        bias = delaymodel.bias
        round_bbv_vec = []
        # floored voltages
        # key: domain ID
        # value: diff b/w rounded and original
        floored = {}
        Ndom = len(bbv_vec)

        # firstly, all of voltages are floored
        for i in range(Ndom):
            v = bbv_vec[i]
            diff = (v * bias - delaymodel.bbv_min * bias)
            step = math.floor(diff / (delaymodel.quant_step * bias))
            rounded = step * delaymodel.quant_step + \
                                    delaymodel.bbv_min
            floored[i] = v - rounded
            round_bbv_vec.append(rounded)

        floored_sorted = sorted(floored.items(), key=lambda x: -x[1])
        while True:
            effvec = delaymodel.delayScale(0.9, \
                        np.array(round_bbv_vec).reshape((Ndom, 1)))
            lat = max(np.matmul(delay_table, effvec))
            if lat < max_lat:
                # no timing violation
                return round_bbv_vec
            elif len(floored_sorted) == 0:
                raise RuntimeError("Fail in voltage rouding")
            else:
                i, _ = floored_sorted[0]
                floored_sorted = floored_sorted[1:]
                round_bbv_vec[i] = round_bbv_vec[i] + \
                                        delaymodel.quant_step


    @staticmethod
    def eval_leak_ilp(CGRA, app, sim_params, individual, leak_optimize):
        """Evaluates leackage power consumption.
            If necessary, it will optimize body bias voltage assignments
                by using integer linear programming.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for simulations
                individual (Individual): An individual to be evaluated
                leak_optimize (bool): True if you need body bias optimization.

            Returns:
                float: leakage power of whole PE array.
        """

        if leak_optimize:
            bb_domains = CGRA.getBBdomains()
            # Probrem Declaration
            problem = pulp.LpProblem()

            # Variable Declaration
            #     1st key: body bias domain
            #     2nd key: body bias voltage
            isBBV = pulp.LpVariable.dicts("isBBV", (bb_domains.keys(), sim_params.bias_range),\
                                             0, 1, cat = "Binary")

            # Problem definition
            problem += pulp.lpSum([isBBV[domain][bbv] * sim_params.PE_leak[bbv] * len(bb_domains[domain]["ALU"]) \
                                    for domain in bb_domains.keys() \
                                    for bbv in sim_params.bias_range])

            # Constraints
            # 1. Body Bias Voltage Exclusivity
            for domain in bb_domains.keys():
                problem += pulp.lpSum(isBBV[domain][bbv] for bbv in sim_params.bias_range) == 1

            # 2. Latancy Satisfaction
            # make delay table
            opcodes = PowerEval.get_opcodes(CGRA, app, individual)
            delay_table = {node: sim_params.delay_info[opcode]
                            for node, opcode in opcodes.items()}

            # make domain table
            #    key: node name, value: domain name
            domain_table = {}
            for node in individual.routed_graph.nodes():
                for domain in bb_domains.keys():
                    if node in bb_domains[domain]["ALU"] or \
                        node in bb_domains[domain]["SE"]:
                        domain_table[node] = domain

            # get maximum latency
            max_lat = app.getClockPeriod(sim_params.getTimeUnit())

            # add constrain for each data path
            for dp in DataPathAnalysis.get_data_path(CGRA, individual):
                problem += pulp.lpSum([(delay_table[node][bbv] if CGRA.isALU(node) \
                                    else sim_params.delay_info["SE"][bbv]) \
                                    * isBBV[domain_table[node]][bbv] \
                                    for node in dp\
                                    for bbv in sim_params.bias_range]) <= max_lat

            # solve this ILP
            # start = time.time()
            stat = problem.solve(ilp_solver)
            # end = time.time()
            # print(end - start, "sec")
            result = problem.objective.value()
            leak_power = pulp.value(problem.objective)

            # check result
            bbv_assign = {}
            if pulp.LpStatus[stat] == "Optimal" and result != None:
                # success
                for domain in bb_domains.keys():
                    for bbv in sim_params.bias_range:
                        if int(isBBV[domain][bbv].value()) == 1:
                            bbv_assign[domain] = bbv
                individual.saveEvaluatedData("body_bias", bbv_assign)
            else:
                individual.saveEvaluatedData("body_bias", {})
                individual.invalidate()
        else:
            PE_leak = sim_params.PE_leak[0]
            width, height = CGRA.getSize()
            leak_power = PE_leak * width * height

        if CGRA.getPregNumber() != 0:
            leak_power += sim_params.preg_leak * CGRA.getPregNumber()

        return leak_power

    @staticmethod
    def eval_glitch(CGRA, app, sim_params, individual, duplicate_enable = False):
        """Evaluates dynamic energy consumption of the PE array considering glitch effects.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for simulations
                individual (Individual): An individual to be evaluated
                duplicate_enable (bool): True if you need the mapped data-flow
                                         to be duplicated horizontally.
            Returns:
                float: evaluated energy consumption.
                        Note that the value does not contain pipeline register &
                        clock tree energy.
        """
        graph = copy.deepcopy(individual.routed_graph)
        graph.add_node("root")
        nx.set_node_attributes(graph, 0, "switching")
        nx.set_node_attributes(graph, 0, "len")
        opcodes = PowerEval.get_opcodes(CGRA, app, individual)

        if CGRA.getPregNumber() != 0:
            stage_domains = CGRA.getStageDomains(individual.preg)
            nx.set_node_attributes(graph, -1, "stage")
            for v in graph.nodes():
                graph.node[v]["stage"] = PowerEval.__getStageIndex(stage_domains, v)
        else:
            nx.set_node_attributes(graph, -1, "stage")

        for i_port in set(individual.routed_graph.nodes()) & set(CGRA.getInputPorts()):
            graph.add_edge("root", i_port)

        # analyze distance from pipeline register
        for u, v in nx.bfs_edges(graph, "root"):
            if CGRA.isALU(v) or CGRA.isSE(v):
                if graph.node[u]["stage"] == graph.node[v]["stage"] and\
                    graph.node[u]["len"] + 1 > graph.node[v]["len"]:
                    graph.node[v]["len"] = graph.node[u]["len"] + 1

        # evaluate glitch propagation
        traversed_list = []
        for u, v in nx.bfs_edges(graph, "root"):
            if v in traversed_list:
                continue
            else:
                traversed_list.append(v)


            if CGRA.isALU(v):
                graph.node[v]["switching"] = sim_params.switching_info[opcodes[v]]
                # propagation part
                if graph.node[v]["len"] > 0:
                    prev_sw = max([graph.node[prev]["switching"] for prev in graph.predecessors(v)])
                    graph.node[v]["switching"] += sim_params.switching_propagation * \
                                                  (sim_params.switching_decay ** graph.node[v]["len"]) * \
                                                  prev_sw

            elif CGRA.isSE(v):
                prev_sws = [graph.node[prev]["switching"] for prev in graph.predecessors(v)]
                prev_sws.append(MIN_SW)
                graph.node[v]["switching"] = max(prev_sws) * sim_params.se_weight


        S_total = sum(nx.get_node_attributes(graph, "switching").values())
              
        if duplicate_enable:
            width, __ = CGRA.getSize()
            S_total *= width // individual.getEvaluatedData("map_width")

        del graph

        return S_total * sim_params.switching_energy

    @staticmethod
    def __getStageIndex(stage_domains, node):
        for stage in range(len(stage_domains)):
            if node in stage_domains[stage]:
                break
        else:
            stage = -1

        return stage


    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Power_Consumption"
