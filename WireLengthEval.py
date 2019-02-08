from EvalBase import EvalBase

class WireLengthEval(EvalBase):
    def __init__(self):
        pass

    def eval(self, CGRA, individual):
        return individual.routing_cost

    def isMinimize(self):
        return True