#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

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
    def eval(CGRA, app, sim_params, individual, **info):
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
        x_coords = []
        SEs = [v for v in individual.routed_graph.nodes() if CGRA.isSE(v)]
        ALUs = [v for v in individual.routed_graph.nodes() if CGRA.isALU(v)]
        width, height = CGRA.getSize()
        for node in SEs + ALUs:
            for x in range(width):
                for y in range(height):
                    rsc = CGRA.get_PE_resources((x, y))
                    if node in  [v for se_set in rsc["SE"].values() for v in se_set ] or \
                        node == rsc["ALU"]:
                        x_coords.append(x)
                        break
        map_width = max(x_coords) + 1
        individual.saveEvaluatedData("map_width", map_width)

        if "quit_minwidth" in info.keys():
            if info["quit_minwidth"] is True:
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