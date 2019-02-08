from EvalBase import EvalBase

class WireLengthEval(EvalBase):
    @staticmethod
    def eval(CGRA, individual):
        print(type(individual), type(CGRA))
        return individual.cost