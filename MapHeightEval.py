from EvalBase import EvalBase

class MapHeightEval(EvalBase):
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

            Saved evaluation results:
                map_width: mapping width

        """
        y_coords = []
        SEs = [v for v in individual.routed_graph.nodes() if CGRA.isSE(v)]
        ALUs = [v for v in individual.routed_graph.nodes() if CGRA.isALU(v)]
        width, height = CGRA.getSize()
        for node in SEs + ALUs:
            for x in range(width):
                for y in range(height):
                    rsc = CGRA.get_PE_resources((x, y))
                    if node in  [v for se_set in rsc["SE"].values() for v in se_set ] or \
                        node == rsc["ALU"]:
                        y_coords.append(y)
                        break
        map_height = max(y_coords) + 1
        return map_height

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Mapping_Height"