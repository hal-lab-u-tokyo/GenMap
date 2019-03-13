from EvalBase import EvalBase

class MapWidthEval(EvalBase):
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
                Options:
                    duplicate_enable (bool): True if you need the mapped data-flow
                                                to be duplicated horizontally.

            Returns:
                int: mapping width

            Saved evaluation results:
                map_width: mapping width

        """
        x_coords = [x for (x, y) in individual.mapping.values()]
        return max(x_coords) - min(x_coords) + 1

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Mapping Width"