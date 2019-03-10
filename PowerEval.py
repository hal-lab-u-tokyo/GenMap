from EvalBase import EvalBase

import networkx as nx
import pulp

PENALTY_VALUE = 1000

class PowerEval(EvalBase):
    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual):
        # save data path
        individual.saveEvaluatedData("data_path", PowerEval.data_path_analysis(CGRA, individual))
        # get body bias domain
        bb_domains = CGRA.getBBdomains()
        if len(bb_domains) != 0 and len(sim_params.bias_range) > 0:
            do_bb_opt = True
        else:
            do_bb_opt = False

        leak_power = PowerEval.__eval_leak(CGRA, app, sim_params, individual, do_bb_opt)
        print(leak_power)
        print(individual.getEvaluatedData("body_bias"))


    @staticmethod
    def data_path_analysis(CGRA, individual):
        # data path analysis
        graph = individual.routed_graph
        used_inports = set(graph.nodes()) & set(CGRA.getInputPorts())
        used_outports = set(graph.nodes()) & set(CGRA.getOutputPorts())
        paths = []
        for i_port in used_inports:
            for o_port in used_outports:
                paths.extend([p[1:-1] for p in nx.all_simple_paths(graph, i_port, o_port)])

        # path separation by activate pipeline register
        if not individual.preg is None:
            data_path = []
            st_domain = CGRA.getStageDomains(individual.preg)
            for p in paths:
                for stage in st_domain:
                    dp = sorted(set(p) & set(stage), key=p.index)
                    if not dp in data_path:
                        data_path.append(dp)
        else:
            data_path = paths

        return data_path

    @staticmethod
    def __eval_leak(CGRA, app, sim_params, individual, leak_optimize):
        if leak_optimize:
            bb_domains = CGRA.getBBdomains()
            # Probrem Declaration
            problem = pulp.LpProblem()

            # Variable Declaration
            #     1st index: body bias domain
            #     2nd index: body bias voltage
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
            # max_lat = 1 / app.getFrequency() * 1000
            max_lat = 20
            opcodes = nx.get_node_attributes(app.getCompSubGraph(), "op")
            delay_table = {CGRA.getNodeName("ALU", pos): sim_params.delay_info[opcodes[op_label]]\
                             for op_label, pos in individual.mapping.items()}
            # make domain table
            domain_table = {}
            for node in individual.routed_graph.nodes():
                for domain in bb_domains.keys():
                    if node in bb_domains[domain]["ALU"] or \
                        node in bb_domains[domain]["SE"]:
                        domain_table[node] = domain

            # add constrain for each data path
            for dp in individual.getEvaluatedData("data_path"):
                print(dp)
                problem += pulp.lpSum([(delay_table[node][bbv] if CGRA.isALU(node) \
                                    else sim_params.delay_info["SE"][bbv]) \
                                    * isBBV[domain_table[node]][bbv] \
                                    for node in dp\
                                    for bbv in sim_params.bias_range]) <= max_lat

            stat = problem.solve()
            result = problem.objective.value()
            leak_power = pulp.value(problem.objective)

            bbv_assign = {}
            if pulp.LpStatus[stat] == "Optimal" and result != None:
                # success
                for domain in bb_domains.keys():
                    for bbv in sim_params.bias_range:
                        if isBBV[domain][bbv].value() == 1:
                            bbv_assign[domain] = bbv
                individual.saveEvaluatedData("body_bias", bbv_assign)
                return leak_power
            else:
                individual.saveEvaluatedData("body_bias", None)
                return PENALTY_VALUE
        else:
            return 0

    @staticmethod
    def __eval_dynamic():
        pass

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Power Consumption"