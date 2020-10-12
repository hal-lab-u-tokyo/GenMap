from EvalBase import EvalBase
import networkx as nx
import os
import signal
import math

main_pid = os.getpid()

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

            Returns:
                int: mapping width

            Saved evaluation results:
                map_width: mapping width

        """
        x_coords = [x for (x, y) in individual.mapping.values()]
        SEs = [v for v in individual.routed_graph.nodes() if CGRA.isSE(v)]
        width, height = CGRA.getSize()
        for se in SEs:
            for x in range(width):
                for y in range(height):
                    rsc = CGRA.get_PE_resources((x, y))
                    if se in  [v for se_set in rsc["SE"].values() for v in se_set ]:
                        x_coords.append(x)
                        break
        map_width = max(x_coords) + 1
        individual.saveEvaluatedData("map_width", map_width)

        min_map = max(len(set(nx.get_node_attributes(app.getInputSubGraph(), "input").keys())),\
                      len(set(nx.get_node_attributes(app.getOutputSubGraph(), "output").keys())),\
                      math.ceil(len(app.getCompSubGraph().nodes()) / height))

        if min_map == map_width and individual.isValid():
            os.kill(main_pid, signal.SIGUSR1)
        return map_width

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Mapping_Width"