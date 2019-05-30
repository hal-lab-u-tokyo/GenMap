from EvalBase import EvalBase
from FaultArchModel import FaultArchModel, CMASOTB2_PE_CONF_PARAM

DEBUG_FIND_BREAK = True

class EccEval(EvalBase):
    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual):
        import os
        PEs_conf = EccEval._get_PEs_conf(CGRA, app, individual)

        env_ecc = bool(int(os.getenv('GENMAP_ECC', '1')))
        env_stack_rate = float(os.getenv('GENMAP_STACK_RATE', '0.02'))
        env_random_seed = int(os.getenv('GENMAP_RANDOM_SEED', '0'))

        faultArchModel_width = 8
        faultArchModel_height = 8
        faultArchModel = FaultArchModel(
            num_pes=faultArchModel_width*faultArchModel_height,
            stack0_rate=env_stack_rate/2, stack1_rate=env_stack_rate/2,
            ecc=env_ecc,seed=env_random_seed)

        for i in range(faultArchModel_width):
            for j in range(faultArchModel_height):
                PE_conf = PEs_conf[i][j]

                for conf_keys in CMASOTB2_PE_CONF_PARAM:
                    if not conf_keys['name'] in PE_conf:
                        PE_conf[conf_keys['name']] = None

                PE_id = i + j * faultArchModel_height
                if not faultArchModel.checkPeAvailablity(PE_id, PE_conf):
                    return 1
        if DEBUG_FIND_BREAK:
            print("Find Vaild Mapping with ECC")
            raise RuntimeError("Find Vaild Mapping with ECC")
        return 0

    @staticmethod
    def _get_PEs_conf(CGRA, app, individual):
        width, height = CGRA.getSize()

        comp_dfg = app.getCompSubGraph()

        routed_graph = individual.routed_graph

        confs = [[{} for y in range(height)] for x in range(width)]

        # ALUs
        for op_label, (x, y) in individual.mapping.items():
            opcode = comp_dfg.node[op_label]["op"]
            confs[x][y]["OPCODE"] = CGRA.getOpConfValue((x, y), opcode)
            alu = CGRA.get_PE_resources((x, y))["ALU"]
            pre_nodes = list(routed_graph.predecessors(alu))
            operands = {
                routed_graph.edges[(v, alu)]["operand"]: v
                for v in pre_nodes if "operand" in routed_graph.edges[(v, alu)]
            }

            if "left" in operands and "right" in operands:
                confs[x][y]["SEL_A"] = CGRA.getNetConfValue(
                    alu, operands["left"])
                confs[x][y]["SEL_B"] = CGRA.getNetConfValue(
                    alu, operands["right"])
            elif "left" in operands:
                confs[x][y]["SEL_A"] = CGRA.getNetConfValue(
                    alu, operands["left"])
                pre_nodes.remove(operands["left"])
                if len(pre_nodes) > 0:
                    confs[x][y]["SEL_B"] = CGRA.getNetConfValue(
                        alu, pre_nodes[0])
            elif "right" in operands:
                confs[x][y]["SEL_B"] = CGRA.getNetConfValue(
                    alu, operands["right"])
                pre_nodes.remove(operands["right"])
                if len(pre_nodes) > 0:
                    confs[x][y]["SEL_A"] = CGRA.getNetConfValue(
                        alu, pre_nodes[0])
            else:
                confs[x][y]["SEL_A"] = CGRA.getNetConfValue(alu, pre_nodes[0])
                if len(pre_nodes) > 1:
                    confs[x][y]["SEL_B"] = CGRA.getNetConfValue(
                        alu, pre_nodes[1])

        # SEs
        for x in range(width):
            for y in range(height):
                se_list = CGRA.get_PE_resources((x, y))["SE"]
                if len(se_list) == 2:
                    # for each SE
                    for se_id, se_sublist in se_list.items():
                        for se in se_sublist:
                            if se in routed_graph.nodes():
                                pre_node = list(
                                    routed_graph.predecessors(se))[0]
                                confs[x][y][CGRA.getWireName(
                                    se)] = CGRA.getNetConfValue(se, pre_node)
                else:
                    raise TypeError("CMA-SOTB2 assumes two SEs per PE")

        return confs

    @staticmethod
    def isMinimize():
        return True

    @staticmethod
    def name():
        return "Mapping_Width"