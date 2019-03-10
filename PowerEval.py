from EvalBase import EvalBase

import networkx as nx

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
    def __eval_dynamic():
        pass

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Power Consumption"