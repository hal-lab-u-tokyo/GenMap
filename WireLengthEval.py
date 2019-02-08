from EvalBase import EvalBase

class WireLengthEval(EvalBase):
    def eval(self, CGRA, individual):
        print(type(individual), type(CGRA))
        return individual.cost