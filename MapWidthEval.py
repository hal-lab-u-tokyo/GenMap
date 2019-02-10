from EvalBase import EvalBase

class MapWidthEval(EvalBase):
    def __init__(self):
        pass

    def eval(self, CGRA, app, individual):
        x_coords = [x for (x, y) in individual.mapping.values()]
        return max(x_coords) - min(x_coords) + 1


    def isMinimize(self):
        return True