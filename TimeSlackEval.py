from EvalBase import EvalBase
from DataPathAnalysis import DataPathAnalysis
import networkx as nx

class TimeSlackEval(EvalBase):

    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual):
        """Return mapping width.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for some simulations
                individual (Individual): An individual to be evaluated

            Returns:
                int: mapping width

        """

        body_bias = individual.getEvaluatedData("body_bias")

        delays = []

        # get delay table for ALU
        op_attr = nx.get_node_attributes(app.getCompSubGraph(), "op")
        delay_table = {CGRA.getNodeName("ALU", pos): \
                        sim_params.delay_info[op_attr[op_label]] \
                            for op_label, pos in individual.mapping.items()}

        delay_table.update({v: sim_params.delay_info["SE"]\
                            for v in individual.routed_graph.nodes() if CGRA.isSE(v)})

        if body_bias is None:
            pass
        else:
            domains = CGRA.getBBdomains()
            domain_table = {}
            for v in individual.routed_graph.nodes():
                for domain_name, resources in domains.items():
                    if CGRA.isALU(v):
                        if v in resources["ALU"]:
                            domain_table[v] = domain_name
                            break
                    elif CGRA.isSE(v):
                        if v in resources["SE"]:
                            domain_table[v] = domain_name
                            break

        delays = []
        for dp in DataPathAnalysis.get_data_path(CGRA, individual):
            if not body_bias is None:
                delays.append(sum([delay_table[v][body_bias[domain_table[v]]] for v in dp]))
            else:
                delays.append(sum([list(delay_table[v].values())[0] for v in dp]))

        time_slack = app.getClockPeriod(sim_params.getTimeUnit()) - max(delays)
        if time_slack < 0:
            individual.invalidate()

        return time_slack

    @staticmethod
    def calc_delay(path, sim_params, body_bias):
        pass

    @staticmethod
    def isMinimize():
        return False

    @staticmethod
    def name():
        return "Time_Slack"