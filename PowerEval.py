from EvalBase import EvalBase
from DataPathAnalysis import DataPathAnalysis

import networkx as nx
import pulp
import copy

PENALTY_COST = 1000

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
        """Return mapping width.

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
        if individual.isValid() == False:
            return PENALTY_COST

        # get body bias domain
        bb_domains = CGRA.getBBdomains()
        if len(bb_domains) != 0 and len(sim_params.bias_range) > 0:
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

        leak_power = PowerEval.eval_leak(CGRA, app, sim_params, individual, do_bb_opt)
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
    def get_opcodes(CGRA, app, mapping):
        """Gets opcodes for each used ALU.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                mapping (dict): mapping of the DFG
                    keys (str): operation label of DFG
                    values (tuple): PE coordinates
            Returns:
                Dict: opcodes of used ALUs
                    keys (str): ALU name of routed graph
                    values (str): opcode of the ALU
        """
        op_attr = nx.get_node_attributes(app.getCompSubGraph(), "op")
        opcodes = {CGRA.getNodeName("ALU", pos): op_attr[op_label]\
                         for op_label, pos in mapping.items()}
        return opcodes

    @staticmethod
    def eval_leak(CGRA, app, sim_params, individual, leak_optimize):
        """Evaluates leackage power consumption.
            If necessary, it will optimize body bias voltage assignments.

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
            opcodes = PowerEval.get_opcodes(CGRA, app, individual.mapping)
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
            stat = problem.solve()
            result = problem.objective.value()
            leak_power = pulp.value(problem.objective)

            # check result
            bbv_assign = {}
            if pulp.LpStatus[stat] == "Optimal" and result != None:
                # success
                for domain in bb_domains.keys():
                    for bbv in sim_params.bias_range:
                        if isBBV[domain][bbv].value() == 1:
                            bbv_assign[domain] = bbv
                individual.saveEvaluatedData("body_bias", bbv_assign)
            else:
                individual.saveEvaluatedData("body_bias", None)
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
        opcodes = PowerEval.get_opcodes(CGRA, app, individual.mapping)

        if CGRA.getPregNumber() != 0:
            stage_domains = CGRA.getStageDomains(individual.preg)
            preg_flag = True
            nx.set_node_attributes(graph, -1, "stage")
            for v in graph.nodes():
                graph.node[v]["stage"] = PowerEval.__getStageIndex(stage_domains, v)
        else:
            preg_flag = False

        for i_port in set(individual.routed_graph.nodes()) & set(CGRA.getInputPorts()):
            graph.add_edge("root", i_port)

        # analyze distance from pipeline register
        for u, v in nx.bfs_edges(graph, "root"):
            if CGRA.isALU(v) or CGRA.isSE(v):
                if preg_flag:
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
            if graph.node[v]["len"] > 0:
                prev_sw = max([graph.node[prev]["switching"] for prev in graph.predecessors(v)])
                if CGRA.isALU(v):
                    graph.node[v]["switching"] += sim_params.switching_propagation * \
                                                    (sim_params.switching_decay ** (graph.node[v]["len"])) * \
                                                    prev_sw

                elif CGRA.isSE(v):
                    graph.node[v]["switching"] = prev_sw * sim_params.se_weight
            else:
                pass


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
