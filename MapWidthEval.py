from EvalBase import EvalBase

class MapWidthEval(EvalBase):
    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, individual):
        x_coords = [x for (x, y) in individual.mapping.values()]
        return max(x_coords) - min(x_coords) + 1

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Mapping Width"