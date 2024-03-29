#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

from EvalBase import EvalBase
from DataPathAnalysis import DataPathAnalysis

import statistics
import signal
import os

import networkx as nx

PENALTY_COST = 1000
main_pid = os.getpid()

class LatencyBalanceEval(EvalBase):
    class DependencyError (Exception):
        pass

    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual, **info):
        """Return latency balance

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for some simulations
                individual (Individual): An individual to be evaluated
                Options:
                    mode (str): to select evaluation mode
                    "max_lat_diff" (default): max latency difference
                                              for all nodes
                    "sum_lat_diff": sum of latency
                                    difference for all nodes
                    "max_path_diff": difference btw the longest data path length
                                     & shortest one
                    "sum_path_diff": sum of path length differences from
                                      the shortest path
            Returns:
                float: evaluated value for the specified mode

        """

        if individual.isValid() == False:
            return PENALTY_COST

        eval_modes = {"max_lat_diff": LatencyBalanceEval.calc_max_lat_diff,
                      "sum_lat_diff": LatencyBalanceEval.calc_sum_lat_diff,
                      "max_path_diff": LatencyBalanceEval.calc_max_path_diff,
                      "sum_path_diff": LatencyBalanceEval.calc_sum_path_diff}

        # get delay_table
        # key:      node name of ALU
        # value:    delay value
        op_attr = nx.get_node_attributes(app.getCompSubGraph(), "opcode")
        delay_table = {CGRA.getNodeName("ALU", pos): \
                        sim_params.delay_info[op_attr[op_label]][0] \
                            for op_label, pos in individual.mapping.items()}

        for v in individual.routed_graph.nodes():
            if not v in delay_table.keys():
                if CGRA.isALU(v):
                    delay_table[v] = sim_params.delay_info[CGRA.getRoutingOpcode(v)][0]
                else:
                    delay_table[v] = 0

        mode = "max_lat_diff" # defualt
        if "mode" in info.keys():
            if info["mode"] in eval_modes.keys():
                mode = info["mode"]
            else:
                print("Error: unknown mode is specified for latency balance evaluation:",
                        info["mode"])
                os.kill(main_pid, signal.SIGUSR1)

        return eval_modes[mode](CGRA, individual, delay_table)

    @staticmethod
    def calc_max_path_diff(CGRA, individual, delay_table):
        len_list = [sum([delay_table[e] for e in dp])\
                     for dp in DataPathAnalysis.get_data_path(CGRA, individual)]
        return max(len_list) - min(len_list)

    @staticmethod
    def calc_sum_path_diff(CGRA, individual, delay_table):
        len_list = [sum([delay_table[e] for e in dp])\
                     for dp in DataPathAnalysis.get_data_path(CGRA, individual)]
        return sum([l - min(len_list) for l in len_list])

    @staticmethod
    def calc_max_lat_diff(CGRA, individual, delay_table):
        lat_diff = LatencyBalanceEval.analyze_latency_diff(CGRA, individual, delay_table)
        return max(lat_diff.values())

    @staticmethod
    def calc_sum_lat_diff(CGRA, individual, delay_table):
        lat_diff = LatencyBalanceEval.analyze_latency_diff(CGRA, individual, delay_table)
        return sum(lat_diff)

    @staticmethod
    def analyze_latency_diff(CGRA, individual, delay_table):
        graph = individual.routed_graph.copy()
        op_nodes = [CGRA.getNodeName("ALU", pos=pos) \
                for pos in individual.mapping.values()]
        graph.add_node("root")
        nx.set_node_attributes(graph, 0.0, "min_len")
        nx.set_node_attributes(graph, 0.0, "max_len")

        used_iport = set(individual.routed_graph.nodes()) & \
                      set(CGRA.getInputPorts())

        for i_port in used_iport:
            graph.add_edge("root", i_port)

        # analyze shortest path length
        for u, v in nx.bfs_edges(graph, "root"):
            if CGRA.isALU(v) or CGRA.isSE(v):
                graph.node[v]["min_len"] = graph.node[u]["min_len"] + delay_table[u]

        # for analyze longest path length
        for u in nx.topological_sort(graph):
            for v in graph.successors(u):
                if CGRA.isALU(v) or CGRA.isSE(v):
                    if graph.node[v]["max_len"] < graph.node[u]["max_len"] + delay_table[u]:
                        graph.node[v]["max_len"] = graph.node[u]["max_len"] + delay_table[u]

        latency_diff = {v: graph.node[v]["max_len"] - graph.node[v]["min_len"] \
                        for v in op_nodes}


        individual.saveEvaluatedData("latency_diff", latency_diff)
        del graph
        return latency_diff


    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Latency_Balance"
