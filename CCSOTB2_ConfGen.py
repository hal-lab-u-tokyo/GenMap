from ConfGenBase import ConfGenBase
from ConfDrawer import ConfDrawer

import os

# ADDRESS
CONST_BASEADDR = 0x00_3000
LD_DMANU_BASEADDR = 0x00_5000
ST_DMANU_BASEADDR = 0x00_6000
PE_CONF_BASEADDR = 0x28_0000
PREG_CONF_ADDR = 0x26_0000

# DATA FOMRATS
CONF_FIELDS = ["OUT_NORTH", "OUT_SOUTH", "OUT_EAST", "OUT_WEST", "OPCODE", "SEL_A", "SEL_B"]
SE_CONF_FORMAT_BIN = "{OUT_NORTH:03b}_{OUT_SOUTH:02b}_{OUT_EAST:03b}_{OUT_WEST:02b}"
ALU_CONF_FORMAT_BIN = "{OPCODE:04b}_{SEL_A:03b}_{SEL_B:03b}"
PE_CONF_FORMAT_BIN = SE_CONF_FORMAT_BIN + "_" + ALU_CONF_FORMAT_BIN
PREG_CONF_FORMAT = "0" * 25 + "_" + "{6:01b}_{5:01b}_{4:01b}_{3:01b}_{2:01b}_{1:01b}_{0:01b}"

TABLE_FORMAT = "0000_0000_{5:04b}_{4:04b}_{3:04b}_{2:04b}_{1:04b}_{0:04b}"
TABLE_FORMAER_OFFSET = 4
TABLE_LATTER_OFFSET = 8
TABLE_MASK_FORMAT = "0000_0000_0000_0000_0000_{11:01b}_{10:01b}_{9:01b}_{8:01b}" + \
                    "_{7:01b}_{6:01b}_{5:01b}_{4:01b}_{3:01b}_{2:01b}_{1:01b}_{0:01b}"
TABLE_MASK_OFFSET = 12


HEAD_FLIT = "001_{addr:022b}_{mt:03b}_{vch:03b}_{src:02b}_{dst:02b}\n"
HEADTAIL_FLIT = "011_{data:s}\n"
MSG_TYPES = {"SW": 1}

class CCSOTB2_ConfGen(ConfGenBase):
    # def generate(self, CGRA, app, individual, eval_list, args):
    def generate(self, header, data, individual_id, args):
        CGRA = header["arch"]
        individual = data["hof"][individual_id]
        app = header["app"]

        ### debug ###
        import xml.etree.ElementTree as ET
        from PEArrayModel import PEArrayModel
        from SimParameters import SimParameters
        tree = ET.ElementTree(file="./CMA_conf.xml")
        pearray = tree.getroot()
        if pearray.tag == "PEArray":
            CGRA = PEArrayModel(pearray)

        try:
            tree = ET.ElementTree(file="./simdata.xml")
        except ET.ParseError as e:
            print("Parse Error", e.args)
            exit()

        sim_xml = tree.getroot()
        try:
            sim_params = SimParameters(CGRA, sim_xml)
        except SimParameters.InvalidParameters as e:
            print("Parameter import failed: ", e.args[0])
        header["sim_params"] = sim_params

        from Application import Application
        app = Application()
        app.read_dot("./af.dot")
        app.setFrequency(30, "M")
        header["app"] = app
        ### debug end ###

        self.force_mode = args["force"]

        if os.path.exists(args["output_dir"]):
            # mapping figure
            fig_filename = args["output_dir"] + "/" + args["prefex"] + "_map.png"
            if os.path.exists(fig_filename) and not self.force_mode:
                print(fig_filename, "exist")
            else:
                drawer = ConfDrawer(CGRA, individual)
                drawer.draw_PEArray(CGRA, individual)
                drawer.save(fig_filename)

                # make configurations
                PE_confs = self.make_PE_conf(CGRA, app, individual)
                ld_conf = self.make_LD_Dmanu(CGRA, individual.routed_graph)
                st_conf = self.make_ST_Dmanu(CGRA, individual.routed_graph)
                const_conf = self.make_Const(CGRA, individual.routed_graph)
                if "duplicate" in args:
                    map_width = individual.getEvaluatedData("map_width")
                    if map_width is None:
                        print("duplicate option ignored because map width was not evaluated")
                    else:
                        self.duplicate(CGRA, PE_confs, ld_conf, st_conf, map_width)

                if self.save_conf(CGRA, PE_confs, const_conf, ld_conf, st_conf, individual.preg, \
                                     args["output_dir"] + "/" + args["prefex"] + "_conf.pkt"):

                    self.save_info(header, individual, individual_id,\
                        args["output_dir"] + "/" + args["prefex"] + "_info.txt")
        else:
            print("No such direcotry: ", args["output_dir"])

    def save_conf(self, CGRA, PE_confs, Const_conf, LD_conf, ST_conf, PREG_conf, filename):
        if os.path.exists(filename) and not self.force_mode:
            print(filename, "exists")
            return False
        else:
            f = open(filename, "w")
            width, height = CGRA.getSize()

            # PE config
            f.write("\n//PE Config\n")
            for x in range(width):
                for y in range(height):
                    if len(PE_confs[x][y]) > 0:
                        addr = 12 * y + x << 8
                        for filed in CONF_FIELDS:
                            if not filed in PE_confs[x][y]:
                                PE_confs[x][y][filed] = 0
                        f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                    vch=0, src=0, dst=1))
                        f.write(HEADTAIL_FLIT.format(data=PE_CONF_FORMAT_BIN.format(**PE_confs[x][y])))

            # PREG Config
            f.write("\n//PREG Config\n")
            addr = PREG_CONF_ADDR
            f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                        vch=0, src=0, dst=1))
            f.write(HEADTAIL_FLIT.format(data=PREG_CONF_FORMAT.format(*PREG_conf)))

            # Const Regs
            f.write("\n//Const Regs\n")
            for i in range(len(Const_conf)):
                addr = CONST_BASEADDR + 4 * i
                f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                            vch=0, src=0, dst=1))
                f.write(HEADTAIL_FLIT.format(data="{0:032b}".format(int(Const_conf[i]))))


            # LD table
            f.write("\n//LD Table\n")
            addr = LD_DMANU_BASEADDR + TABLE_FORMAER_OFFSET
            f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                    vch=0, src=0, dst=1))
            f.write(HEADTAIL_FLIT.format(data=TABLE_FORMAT.format(*LD_conf["table"][0:6])))

            addr = LD_DMANU_BASEADDR + TABLE_LATTER_OFFSET
            f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                    vch=0, src=0, dst=1))
            f.write(HEADTAIL_FLIT.format(data=TABLE_FORMAT.format(*LD_conf["table"][6:12])))


            addr = LD_DMANU_BASEADDR + TABLE_MASK_OFFSET
            f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                    vch=0, src=0, dst=1))
            f.write(HEADTAIL_FLIT.format(data=TABLE_MASK_FORMAT.format(*LD_conf["mask"])))


            # ST table
            f.write("\n//ST Table\n")
            addr = ST_DMANU_BASEADDR + TABLE_FORMAER_OFFSET
            f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                    vch=0, src=0, dst=1))
            f.write(HEADTAIL_FLIT.format(data=TABLE_FORMAT.format(*ST_conf["table"][0:6])))

            addr = ST_DMANU_BASEADDR + TABLE_LATTER_OFFSET
            f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                    vch=0, src=0, dst=1))
            f.write(HEADTAIL_FLIT.format(data=TABLE_FORMAT.format(*ST_conf["table"][6:12])))


            addr = ST_DMANU_BASEADDR + TABLE_MASK_OFFSET
            f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                    vch=0, src=0, dst=1))
            f.write(HEADTAIL_FLIT.format(data=TABLE_MASK_FORMAT.format(*ST_conf["mask"])))

            f.close()

            return True

    def duplicate(self, CGRA, PE_confs, ld_conf, st_conf, map_width):
        width, height = CGRA.getSize()
        out_num = len(st_conf["mem_align"])
        in_num = len(ld_conf["mem_align"])
        for dup_count in range(1, width // map_width):
            for x in range(map_width):
                dest_x = map_width * dup_count + x
                # LD table
                ld_conf["table"][dest_x] = ld_conf["table"][x] \
                                            + in_num * dup_count
                ld_conf["mask"][dest_x] = ld_conf["mask"][x]

                for y in range(height):
                    PE_confs[dest_x][y] = PE_confs[x][y]
            # ST table
            for out_idx in range(out_num):
                st_conf["table"][out_idx + dup_count * out_num] = st_conf["table"][out_idx] + map_width * dup_count
                st_conf["mask"][out_idx + dup_count * out_num] = st_conf["mask"][out_idx]


            # add in/out data
            for in_idx in range(in_num):
                ld_conf["mem_align"].append(ld_conf["mem_align"][in_idx] + "_" + str(dup_count))
            for out_idx in range(out_num):
                st_conf["mem_align"].append(st_conf["mem_align"][out_idx] + "_" + str(dup_count))


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

    def make_LD_Dmanu(self, CGRA, routed_graph):

        aligned_input_data = list(set([routed_graph.nodes[i]["map"] for i in CGRA.getInputPorts() \
                                if i in routed_graph.nodes()]))
        aligned_input_data.sort()
        inport_num = len(CGRA.getInputPorts())

        ld_conf = {"table": [0 for i in range(inport_num)], \
                    "mask": [False for i in range(inport_num)], \
                    "mem_align": aligned_input_data}
        for i in range(inport_num):
            port_name = CGRA.getNodeName("IN_PORT", index=i)
            if port_name in routed_graph.nodes():
                ld_conf["table"][i] = aligned_input_data.index(routed_graph.nodes[port_name]["map"])
                ld_conf["mask"][i]= True

        return ld_conf


    def make_ST_Dmanu(self, CGRA, routed_graph):

        aligned_output_data = list(set([routed_graph.nodes[i]["map"] for i in CGRA.getOutputPorts() \
                                if i in routed_graph.nodes()]))
        aligned_output_data.sort()

        out_port_num = len(CGRA.getOutputPorts())
        out_port_indexs = {CGRA.getNodeName("OUT_PORT", index=i): i \
                            for i in range(out_port_num) }

        st_conf = {"table": [0 for i in range(out_port_num)], \
                    "mask": [False for i in range(out_port_num)], \
                    "mem_align": aligned_output_data}

        for i in range(len(aligned_output_data)):
            out_data = aligned_output_data[i]
            for v, idx in out_port_indexs.items():
                if v in routed_graph.nodes():
                    if routed_graph.nodes[v]["map"] == out_data:
                        st_conf["table"][i] = idx
                        st_conf["mask"][i] = True
                        break

        return st_conf

    def make_Const(self, CGRA, routed_graph):
        const_num = len(CGRA.getConstRegs())
        const_conf = [0 for i in range(const_num)]

        for i in range(const_num):
            c_reg = CGRA.getNodeName("Const", index=i)
            if c_reg in routed_graph.nodes():
                const_conf[i] = routed_graph.nodes[c_reg]["value"]

        return const_conf

    def save_info(self, header, individual, individual_id, filename):
        if os.path.exists(filename) and not self.force_mode:
            print(filename, "exists")
        else:
            app = header["app"]
            sim_params = header["sim_params"]

            f = open(filename, "w")
            # save ID
            f.write("ID: " + str(individual_id) + "\n\n")

            # save app name
            f.write("APP: " + app.getAppName() + "\n\n")

            # save frequency
            f.write("Clock Frequncy: {0}MHz\n\n".format(app.getFrequency("M")))

            # units setting
            f.write("Units setting\n")
            f.write("Time: " + sim_params.getTimeUnit() + "\n")
            f.write("Power: " + sim_params.getPowerUnit() + "\n")
            f.write("Energy: " + sim_params.getEnergyUnit() + "\n")
            f.write("\n")

            # evaluated data
            f.write("Evaluation results\n")
            for eval_name, value in zip(header["eval_names"], individual.fitness.values):
                f.write("{0}: {1}\n".format(eval_name, value))

            # Other data
            leak = individual.getEvaluatedData("leakage_power")
            dynamic = individual.getEvaluatedData("dynamic_power")
            if not leak is None:
                f.write("Leakage Power: {0}\n".format(leak))

            if not dynamic is None:
                f.write("Dynamic Power: {0}\n".format(dynamic))

            body_bias = individual.getEvaluatedData("body_bias")
            if not body_bias is None:
                f.write("\nBody Bias Voltages\n")
                for domain, voltage in body_bias.items():
                    f.write("{0}: {1} V\n".format(domain, voltage))


            f.close()

if __name__ == '__main__':
    generator = CCSOTB2_ConfGen()
    generator.main()
