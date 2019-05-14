from EvalBase import EvalBase


CMASOTB2_PE_CONF_PARAM = [
    {
        'name': 'OPCODE',
        'width': '4'
    }, {
        'name': 'SEL_A',
        'width': '3'
    }, {
        'name': 'SEL_B',
        'width': '3'
    }, {
        'name': 'OUT_A_NORTH',
        'width': '3'
    }, {
        'name': 'OUT_A_SOUTH',
        'width': '2'
    }, {
        'name': 'OUT_A_EAST',
        'width': '3'
    }, {
        'name': 'OUT_A_WEST',
        'width': '2'
    }, {
        'name': 'OUT_B_NORTH',
        'width': '4'
    }, {
        'name': 'OUT_B_EAST',
        'width': '3'
    }, {
        'name': 'OUT_B_WEST',
        'width': '3'
    }
]

class EccEval(EvalBase):
    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual):

        PEs_conf = EccEval._get_PEs_conf(CGRA, app, individual)

        for i in range(8):
            for j in range(8):
                PE_conf = PEs_conf[i][j]

                for conf_keys in CMASOTB2_PE_CONF_PARAM:
                    if not conf_keys['name'] in PE_conf:
                        PE_conf[conf_keys['name']] = None

                print('PE_conf:', PE_conf)

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