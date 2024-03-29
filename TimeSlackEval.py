#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

from EvalBase import EvalBase
from DataPathAnalysis import DataPathAnalysis
import networkx as nx

PENALTY_COST = -1000

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
        fastest_mode = False

        if individual.isValid() == False:
            if not body_bias is None:
                if len(body_bias) == 0:
                    # in case of failure in body bias assign
                    fastest_mode = True
            else:
                return PENALTY_COST


        delays = []

        # get delay table for ALU
        # key:      node name of ALU
        # value:    list of delay value for each body bias voltage
        op_attr = nx.get_node_attributes(app.getCompSubGraph(), "opcode")
        delay_table = {CGRA.getNodeName("ALU", pos): \
                        sim_params.delay_info[op_attr[op_label] if op_label in op_attr.keys() else "CAT" ] \
                            for op_label, pos in individual.mapping.items()}

        delay_table.update({v: sim_params.delay_info["SE"]\
                            for v in individual.routed_graph.nodes() if CGRA.isSE(v)})

        # for routing ALU
        for alu, flag in nx.get_node_attributes(individual.routed_graph,\
                                                 "route").items():
            if flag:
                delay_table[alu] = sim_params.delay_info[\
                        CGRA.getRoutingOpcode(alu)]

        if not body_bias is None:
            domains = CGRA.getBBdomains()
            if fastest_mode:
                # find fastest body bias voltage
                fastest_bb = sorted(sim_params.delay_info["SE"])[-1]
                body_bias = {domain_name: fastest_bb for domain_name in domains.keys()}
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
