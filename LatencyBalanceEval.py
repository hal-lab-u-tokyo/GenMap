from EvalBase import EvalBase
from DataPathAnalysis import DataPathAnalysis

import networkx as nx

PENALTY_COST = 1000


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
                    duplicate_enable (bool): True if you need the mapped data-flow
                                                to be duplicated horizontally.

            Returns:
                float: coefficient of variation of all path latency

        """

        if individual.isValid() == False:
            return PENALTY_COST

        lat_list = [len(dp) for dp in DataPathAnalysis.get_data_path(CGRA, individual)]

        return max(lat_list) - min(lat_list)

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Latency_Balance"
