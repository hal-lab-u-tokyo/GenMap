from ConfGenBase import ConfGenBase
from ConfDrawer import ConfDrawer

import os
import math

# DATA FOMRATS
SE_FIELDS = ["OUT_A_NORTH", "OUT_A_SOUTH", "OUT_A_EAST", "OUT_A_WEST", \
                "OUT_B_NORTH", "OUT_B_EAST", "OUT_B_WEST"]
ALU_FIELDS = ["OPCODE", "SEL_A", "SEL_B"]
SE_CONF_FORMAT_BIN = "{OUT_A_NORTH:03b}_{OUT_A_SOUTH:03b}_{OUT_A_EAST:03b}_{OUT_A_WEST:03b}" + \
                        "{OUT_B_NORTH:03b}_{OUT_B_EAST:03b}_{OUT_B_WEST:03b}"
ALU_CONF_FORMAT_BIN = "{OPCODE:04b}_{SEL_A:03b}_{SEL_B:03b}"

ALU_CONF_PKT = "100000_00000000000__1111__{CONF:s}__{ROW:08b}__{COL:08b} //PE Config\n"
SE_CONF_PKT = "100001_0000__{CONF:s}__{ROW:08b}__{COL:08b} //SE Config\n"
CONST_PKT = "100010_00_{index:04b}_000__{CONST:016b}__0000000000000000 //Constant\n"
TAIL_PKT = "111111_000000_000_0000000000000000__0000000000000000 // others\n"

TABLE_FORMAT = "{7:03b}_{6:03b}_{5:03b}_{4:03b}_{3:03b}_{2:03b}_{1:03b}_{0:03b}"
TABLE_MASK_FORMAT = "_{7:01b}_{6:01b}_{5:01b}_{4:01b}_{3:01b}_{2:01b}_{1:01b}_{0:01b}"
LD_TABLE_PKT = "0011000_{index:04b}0_0_{TABLE:s} //LD TABLE\n"
LD_MASK_PKT  = "0011000_{index:04b}1_0_00000000_00000000{MASK:s} //LD MASK\n"
ST_TABLE_PKT = "0100000_{index:04b}0_0_{TABLE:s} //ST TABLE\n"
ST_MASK_PKT  = "0100000_{index:04b}1_0_00000000_00000000{MASK:s} //ST MASK\n"

class CMASOTB2_ConfGen(ConfGenBase):
    # def generate(self, CGRA, app, individual, eval_list, args):
    def generate(self, header, data, individual_id, args):
        CGRA = header["arch"]
        individual = data["hof"][individual_id]
        app = header["app"]

        self.force_mode = args["force"]

        if os.path.exists(args["output_dir"]):

            fig_filename = args["output_dir"] + "/" + args["prefex"] + "_map.png"
            confp_filename = args["output_dir"] + "/" + args["prefex"] + "_confp.dat"
            table_filename = args["output_dir"] + "/" + args["prefex"] + "_table.dat"
            info_filename = args["output_dir"] + "/" + args["prefex"] + "_info.txt"

            # check if files exist
            files_exist = False
            if self.force_mode != True:
                files_exist |= os.path.exists(fig_filename)
                files_exist |= os.path.exists(confp_filename)
                files_exist |= os.path.exists(table_filename)
                files_exist |= os.path.exists(info_filename)

            if files_exist:
                print("some file exist")
            else:
                # mapping figure
                drawer = ConfDrawer(CGRA, individual)
                drawer.draw_PEArray(CGRA, individual, app)
                drawer.save(fig_filename)

                # make configurations
                PE_confs = self.make_PE_conf(CGRA, app, individual)
                ld_conf = self.make_LD_Dmanu(CGRA, individual.routed_graph)
                st_conf = self.make_ST_Dmanu(CGRA, individual.routed_graph)
                const_conf = self.make_Const(CGRA, individual.routed_graph)
                if "duplicate" in args["style"]:
                    map_width = individual.getEvaluatedData("map_width")
                    if map_width is None:
                        print("duplicate option ignored because map width was not evaluated")
                        self.save_confp(CGRA, PE_confs, const_conf, confp_filename)
                        self.save_table(CGRA, ld_conf, st_conf, table_filename)
                    else:
                        self.save_confp(CGRA, PE_confs, const_conf, confp_filename, True, map_width)
                        self.save_table(CGRA, ld_conf, st_conf, table_filename, True, map_width)
                else:
                    self.save_confp(CGRA, PE_confs, const_conf, confp_filename)
                    self.save_table(CGRA, ld_conf, st_conf, table_filename)

                self.save_info(header, individual, individual_id, ld_conf, st_conf, info_filename)

        else:
            print("No such direcotry: ", args["output_dir"])

    def save_confp(self, CGRA, PE_confs, Const_conf, filename, duplicate = False,\
                    map_width = 0):

        f = open(filename, "w")
        width, height = CGRA.getSize()

        if duplicate:
            dup_count = width // map_width
        else:
            dup_count = 1
            map_width = width

        # PE config
        for x in range(map_width):
            col = 0
            for i in range(dup_count):
                col = col << map_width
                col += (1 << x)
            for y in range(height):
                row = 1 << y
                if len(PE_confs[x][y]) > 0:
                    alu_conf = {k: v for k, v in PE_confs[x][y].items() if k in ALU_FIELDS}
                    se_conf = {k: v for k, v in PE_confs[x][y].items() if k in SE_FIELDS}
                    if len(alu_conf) > 0:
                        for filed in ALU_FIELDS:
                            if not filed in alu_conf:
                                alu_conf[filed] = 0
                        f.write(ALU_CONF_PKT.format(CONF=ALU_CONF_FORMAT_BIN.format(**alu_conf), \
                                                ROW=row, COL=col))
                    if len(se_conf) > 0:
                        for filed in SE_FIELDS:
                            if not filed in se_conf:
                                se_conf[filed] = 0
                    f.write(SE_CONF_PKT.format(CONF=SE_CONF_FORMAT_BIN.format(**se_conf), \
                                                ROW=row, COL=col))

        # Const Regs
        for i in range(len(Const_conf)):
            f.write(CONST_PKT.format(index=i, CONST=int(Const_conf[i])))
        f.close()

        return True

    def save_table(self, CGRA, ld_conf, st_conf, filename, duplicate = False, map_width = 0):
        width, height = CGRA.getSize()
        out_num = len(st_conf["mem_align"])
        in_num = len(ld_conf["mem_align"])
        for dup_count in range(1, width // map_width if duplicate else 1):
            for x in range(map_width):
                dest_x = map_width * dup_count + x
                # LD table
                ld_conf["table"][dest_x] = ld_conf["table"][x] \
                                            + in_num * dup_count
                ld_conf["mask"][dest_x] = ld_conf["mask"][x]

            # ST table
            for out_idx in range(out_num):
                st_conf["table"][out_idx + dup_count * out_num] = st_conf["table"][out_idx] + map_width * dup_count
                st_conf["mask"][out_idx + dup_count * out_num] = st_conf["mask"][out_idx]


            # add in/out data
            for in_idx in range(in_num):
                ld_conf["mem_align"].append(ld_conf["mem_align"][in_idx] + "_(" + str(dup_count) + ")")
            for out_idx in range(out_num):
                st_conf["mem_align"].append(st_conf["mem_align"][out_idx] + "_(" + str(dup_count) + ")")

        ld_data_size = len(ld_conf["mem_align"])
        ld_table_num = (width * ld_data_size // math.gcd(width, ld_data_size)) // ld_data_size

        st_data_size = len(st_conf["mem_align"])
        st_table_num = (width * st_data_size // math.gcd(width, st_data_size)) // st_data_size

        with open(filename, "w") as f:
            for i in range(ld_table_num):
                table = [(v + (ld_data_size * i)) % width for v in ld_conf["table"]]
                f.write(LD_TABLE_PKT.format(TABLE=TABLE_FORMAT.format(*table), index=i))
                f.write(LD_MASK_PKT.format(MASK=TABLE_MASK_FORMAT.format(*ld_conf["mask"]), index=i))
            for i in range(st_table_num):
                table = [st_conf["table"][j - ((st_data_size * i) % width)] \
                            for j in range(len(st_conf["table"]))]
                mask = [st_conf["mask"][j - ((st_data_size * i) % width)] \
                            for j in range(len(st_conf["mask"]))]
                f.write(ST_TABLE_PKT.format(TABLE=TABLE_FORMAT.format(*table), index=i))
                f.write(ST_MASK_PKT.format(MASK=TABLE_MASK_FORMAT.format(*mask), index=i))


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
                pre_nodes.remove(operands["left"])
                if len(pre_nodes) > 0:
                    confs[x][y]["SEL_B"] = CGRA.getNetConfValue(alu, pre_nodes[0])
            elif "right" in operands:
                confs[x][y]["SEL_B"] = CGRA.getNetConfValue(alu, operands["right"])
                pre_nodes.remove(operands["right"])
                if len(pre_nodes) > 0:
                    confs[x][y]["SEL_A"] = CGRA.getNetConfValue(alu, pre_nodes[0])
            else:
                confs[x][y]["SEL_A"] = CGRA.getNetConfValue(alu, pre_nodes[0])
                if len(pre_nodes) > 1:
                    confs[x][y]["SEL_B"] = CGRA.getNetConfValue(alu, pre_nodes[1])

        # SEs
        for x in range(width):
            for y in range(height):
                se_list = CGRA.get_PE_resources((x, y))["SE"]
                if len(se_list) == 2:
                    # for each SE
                    for se_id, se_sublist in se_list.items():
                        for se in se_sublist:
                            if se in routed_graph.nodes():
                                pre_node = list(routed_graph.predecessors(se))[0]
                                confs[x][y][CGRA.getWireName(se)] = CGRA.getNetConfValue(se, pre_node)
                else:
                    raise TypeError("CMA-SOTB2 assumes two SEs per PE")

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

    def save_info(self, header, individual, individual_id, LD_conf, ST_conf, filename):
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

            # data memory alignment
            f.write("\n")
            f.write("Input data alignment\n")
            f.write(str(LD_conf["mem_align"]))
            f.write("\n\n")
            f.write("Output data alignment\n")
            f.write(str(ST_conf["mem_align"]))

            f.close()

if __name__ == '__main__':
    generator = CMASOTB2_ConfGen()
    generator.main()
