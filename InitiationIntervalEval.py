#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Masato Nakagawa

import math
from random import weibullvariate
from EvalBase import EvalBase


class InitiationIntervalEval(EvalBase):
    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual):
        """Return initial interval.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for some simulations
                individual (Individual): An individual to be evaluated

            Returns:
                int: initial interval

        """
        coords = []
        SEs = [v for v in individual.routed_graph.nodes() if CGRA.isSE(v)]
        ALUs = [v for v in individual.routed_graph.nodes() if CGRA.isALU(v)]
        width, height = CGRA.getSize()
        for node in SEs + ALUs:
            for x in range(width):
                for y in range(height):
                    rsc = CGRA.get_PE_resources((x, y))
                    if node in [v for se_set in rsc["SE"].values() for v in se_set] or \
                            node == rsc["ALU"]:
                        coords.append((x, y))
                        break

        II_min = math.ceil(len(app.getCompSubGraph().nodes()) / width)
        II_max = height
        II = II_max

        for ii in range(II_min, II_max + 1):
            shifted_coords = [(x, y + ii) for (x, y) in coords]
            common_coords = list(set(coords) & set(shifted_coords))
            if len(common_coords) == 0:
                II = ii
                break

        return II

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Initial_Interval"
