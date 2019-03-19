from ConfGenBase import ConfGenBase
from ConfDrawer import ConfDrawer

import os

CONF_FIELDS = ["OUT_NORTH", "OUT_SOUTH", "OUT_EAST", "OUT_WEST", "OPCODE", "SEL_A", "SEL_B"]
SE_CONF_FORMAT_BIN = "{OUT_NORTH:03b}_{OUT_SOUTH:02b}_{OUT_EAST:03b}_{OUT_WEST:02b}"
ALU_CONF_FORMAT_BIN = "{OPCODE:04b}_{SEL_A:03b}_{SEL_B:03b}"
PE_CONF_FORMAT_BIN = SE_CONF_FORMAT_BIN + "_" + ALU_CONF_FORMAT_BIN

HEAD_FLIT = "001_{addr:022b}_{mt:03b}_{vch:03b}_{src:02b}_{dst:02b}\n"
HEADTAIL_FLIT = "011_{data:032b}\n\n"
MSG_TYPES = {"SW": 1}

class CCSOTB2_ConfGen(ConfGenBase):
    def generate(self, CGRA, app, individual, eval_list, args):
        ### debug ###
        import xml.etree.ElementTree as ET
        from PEArrayModel import PEArrayModel
        tree = ET.ElementTree(file="./CMA_conf.xml")
        pearray = tree.getroot()
        if pearray.tag == "PEArray":
            CGRA = PEArrayModel(pearray)
        ### debug end ###

        self.force_mode = args["force"]

        if os.path.exists(args["output_dir"]):
            # mapping figure
            # drawer = ConfDrawer(CGRA, individual)
            # drawer.draw_PEArray(CGRA, individual)
            # drawer.save(args["output_dir"] + "/" + args["prefex"] + "_map.png")
            confs = self.make_PE_conf(CGRA, app, individual)
            self.save_PE_conf(CGRA, confs, args["output_dir"] + "/" + args["prefex"] + "_conf.pkt")

        else:
            print("No such direcotry: ", args["output_dir"])

    def save_PE_conf(self, CGRA, confs, filename):
        if os.path.exists(filename) and not self.force_mode:
            print(filename, "exists")
            return False
        else:
            f = open(filename, "w")
            width, height = CGRA.getSize()
            for x in range(width):
                for y in range(height):
                    if len(confs[x][y]) > 0:
                        addr = 12 * y + x << 8
                        for filed in CONF_FIELDS:
                            if not filed in confs[x][y]:
                                confs[x][y][filed] = 0
                        f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                    vch=0, src=0, dst=1))
                        f.write(HEADTAIL_FLIT.format(data=int(PE_CONF_FORMAT_BIN.format(**confs[x][y]),2)))

            f.close()

    def make_PE_conf(self, CGRA, app, individual):
        width, height = CGRA.getSize()

        comp_dfg = app.getCompSubGraph()

        routed_graph = individual.routed_graph

        confs = [ [ {} for y in range(height)] for x in range(width)]

        # ALUs
        for op_label, (x, y) in individual.mapping.items():
            opcode = comp_dfg.node[op_label]["op"]
            confs[x][y]["OPCODE"] = CGRA.getOpConfValue((x, y), opcode)
            alu = CGRA.get_PE_resources((x, y))["ALU"]
            pre_nodes = list(routed_graph.predecessors(alu))
            operands = {routed_graph.edges[(v, alu)]["operand"]: v \
                        for v in pre_nodes\
                        if "operand" in routed_graph.edges[(v, alu)]}

            if "left" in operands and "right" in operands:
                confs[x][y]["SEL_A"] = CGRA.getNetConfValue(alu, operands["left"])
                confs[x][y]["SEL_B"] = CGRA.getNetConfValue(alu, operands["right"])
            elif "left" in operands:
                confs[x][y]["SEL_A"] = CGRA.getNetConfValue(alu, operands["left"])
                pre_nodes.pop(v)
                if len(pre_nodes) > 0:
                    confs[x][y]["SEL_B"] = CGRA.getNetConfValue(alu, pre_nodes[0])
                else:
                    confs[x][y]["SEL_B"] = None
            elif "right" in operands:
                confs[x][y]["SEL_B"] = CGRA.getNetConfValue(alu, operands["right"])
                pre_nodes.pop(v)
                if len(pre_nodes) > 0:
                    confs[x][y]["SEL_A"] = CGRA.getNetConfValue(alu, pre_nodes[0])
                else:
                    confs[x][y]["SEL_A"] = None
            else:
                confs[x][y]["SEL_A"] = CGRA.getNetConfValue(alu, pre_nodes[0])
                if len(pre_nodes) > 1:
                    confs[x][y]["SEL_B"] = CGRA.getNetConfValue(alu, pre_nodes[1])
                else:
                    confs[x][y]["SEL_B"] = None

        # SEs
        for x in range(width):
            for y in range(height):
                se_list = CGRA.get_PE_resources((x, y))["SE"]
                if len(se_list) == 1:
                    # for each SE outputs
                    for se in list(se_list.values())[0]:
                        if se in routed_graph.nodes():
                            pre_node = list(routed_graph.predecessors(se))[0]
                            confs[x][y][CGRA.getWireName(se)] = CGRA.getNetConfValue(se, pre_node)
                else:
                    raise TypeError("CCSOTB2 assumes one SE per PE")

        return confs

    def compress_confdata():
        pass

    def generate_Input_Dmanu():
        pass

    def generate_Output_Dmanu():
        pass

    def save_Info():
        pass

if __name__ == '__main__':
    generator = CCSOTB2_ConfGen()
    generator.main()
