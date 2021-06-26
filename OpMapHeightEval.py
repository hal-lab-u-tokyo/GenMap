#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

from EvalBase import EvalBase

class OpMapHeightEval(EvalBase):
    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual):
        """Return op mapping height.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for some simulations
                individual (Individual): An individual to be evaluated

            Returns:
                int: op mapping height

        """
        y_coords = [y for (x, y) in individual.mapping.values()]
        map_width = max(y_coords) + 1
        return map_width

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Op_Mapping_Height"