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
        return "Wire Length"