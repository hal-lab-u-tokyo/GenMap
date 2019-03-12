from EvalBase import EvalBase

import networkx as nx
import pulp
import copy

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

        leak_power = PowerEval.eval_leak(CGRA, app, sim_params, individual, do_bb_opt)
        # print(leak_power)
        print(individual.getEvaluatedData("body_bias"))
        # PowerEval.eval_dynamic(CGRA, app, sim_params, individual)


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
        if CGRA.getPregNumber() != 0:
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
    def get_opcodes(CGRA, app, mapping):
        op_attr = nx.get_node_attributes(app.getCompSubGraph(), "op")
        opcodes = {CGRA.getNodeName("ALU", pos): op_attr[op_label]\
                         for op_label, pos in mapping.items()}
        return opcodes

    @staticmethod
    def eval_leak(CGRA, app, sim_params, individual, leak_optimize):
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
            max_lat = app.getClockPeriod(sim_params.getTimeUnit())
            print(max_lat)
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

            # add constrain for each data path
            for dp in individual.getEvaluatedData("data_path"):
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
        else:
            PE_leak = sim_params.PE_leak[0]
            width, height = CGRA.getSize()
            leak_power = PE_leak * width * height

        if CGRA.getPregNumber() != 0:
            leak_power += sim_params.preg_leak * CGRA.getPregNumber()

        return leak_power

    @staticmethod
    def eval_dynamic(CGRA, app, sim_params, individual):
        stage_domains = CGRA.getStageDomains(individual.preg)
        graph = copy.deepcopy(individual.routed_graph)
        graph.add_node("root")
        nx.set_node_attributes(graph, 0, "switching")
        nx.set_node_attributes(graph, 0, "len")
        opcodes = PowerEval.get_opcodes(CGRA, app, individual.mapping)

        if CGRA.getPregNumber() != 0:
            preg_flag = True
            nx.set_node_attributes(graph, -1, "stage")
            for v in graph.nodes():
                graph.node[v]["stage"] = PowerEval.__getStageIndex(stage_domains, v)

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
                    print(v, "prev", prev_sw)
                    graph.node[v]["switching"] += sim_params.switching_propagation * \
                                                    (sim_params.switching_damp ** (graph.node[v]["len"] - 1)) * \
                                                    prev_sw
                elif CGRA.isSE(v):
                    graph.node[v]["switching"] = prev_sw


        print(nx.get_node_attributes(graph, "switching"))
        S_total = sum(nx.get_node_attributes(graph, "switching").values())

        print(S_total)

        del graph
        if preg_flag:
            return S_total * sim_params.switching_energy + \
                    sum(individual.preg) * sim_params.preg_dynamic_energy
        else:
            return S_total * sim_params.switching_energy

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
        return "Power Consumption"