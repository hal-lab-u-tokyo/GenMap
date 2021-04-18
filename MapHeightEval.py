from EvalBase import EvalBase
import networkx as nx
import os
import signal
import math

main_pid = os.getpid()

class MapHeightEval(EvalBase):
    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual, **info):
        """Return mapping height.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for some simulations
                individual (Individual): An individual to be evaluated

            Returns:
                int: mapping height

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

        # if "quit_minheight" in info.keys():
        #     if info["quit_minheight"] is True:
        #         input_count = len(set(nx.get_node_attributes(\
        #                     app.getInputSubGraph(), "input").keys()))
        #         output_count = len(set(nx.get_node_attributes(\
        #                     app.getOutputSubGraph(), "output").keys()))
        #         minh_op = math.ceil(len(app.getCompSubGraph().nodes()) \
        #                                 / width)
        #         if CGRA.isIOShared():
        #             min_maph = max(((input_count + output_count + 1) // 2),\
        #                             minh_op)
        #         else:
        #             min_maph = max(input_count, output_count, minh_op)

        #     if min_maph == map_height and individual.isValid():
        #         os.kill(main_pid, signal.SIGUSR1)

        return map_height

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Mapping_Height"