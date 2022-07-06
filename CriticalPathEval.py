#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

from EvalBase import EvalBase
from DataPathAnalysis import DataPathAnalysis

class CriticalPathEval(EvalBase):
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
        return max([len(dp) for dp in  DataPathAnalysis.get_data_path(CGRA, individual)])

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Critical_Path"