#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

from EvalBase import EvalBase

class WireLengthEval(EvalBase):
    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual):
        return individual.routing_cost

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Wire_Length"