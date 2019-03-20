from EvalBase import EvalBase

class OpMapWidthEval(EvalBase):
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
        x_coords = [x for (x, y) in individual.mapping.values()]
        map_width = max(x_coords) + 1
        return map_width

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Op_Mapping_Width"