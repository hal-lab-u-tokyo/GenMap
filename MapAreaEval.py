from EvalBase import EvalBase
from MapHeightEval import MapHeightEval
from MapWidthEval import MapWidthEval

class MapAreaEval(EvalBase):
    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual):
        return MapHeightEval.eval(CGRA, app, sim_params, individual) * \
                MapWidthEval.eval(CGRA, app, sim_params, individual)

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Map_Area"