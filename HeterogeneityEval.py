#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

from EvalBase import EvalBase
import math

PENALTY_COST = 1000

class HeterogeneityEval(EvalBase):
    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual):
        """Return heterogeneity

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for some simulations
                individual (Individual): An individual to be evaluated

            Returns:
                float: heterogeneity
                    0 means a valid mapping

        """
        cost = 0.0
        used_alus = set(individual.mapping.values())
        invalid = False
        dfg = app.getCompSubGraph()
        for opnode, pos in individual.mapping.items():
            op = dfg.nodes[opnode]["opcode"]
            alu_coords = set(CGRA.getSupportedALUs(op))
            if not pos in alu_coords:
                invalid = True
                # find nearest free alu
                dis = [ (pos[0] - x) ** 2 + (pos[1] - y) ** 2\
                         for (x, y) in alu_coords - used_alus]
                if len(dis) == 0:
                    cost += PENALTY_COST
                else:
                    cost += min(dis)

        if invalid:
            individual.invalidate()

        return cost

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Heterogeneity"