#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

import os
from tkinter import TclError

from ConfGenBase import ConfGenBase
from ConfDrawer import ConfDrawer
from ConfCompress import ConfCompressor

# ADDRESS
CONST_BASEADDR = 0x00_3000
LD_DMANU_BASEADDR = 0x00_5000
ST_DMANU_BASEADDR = 0x00_6000
ALU_RMC_ADDR = 0x20_0000
SE_RMC_ADDR = 0x21_0000
PE_CONF_BASEADDR = 0x28_0000
PREG_CONF_ADDR = 0x26_0000

# DATA FOMRATS
CONF_FORMAT = {'OPCODE': 4, 'SEL_A': 3, 'SEL_B': 3, 'OUT_NORTH': 3, 'OUT_SOUTH': 2, 'OUT_EAST': 3, 'OUT_WEST': 2}
RMC_PATTERN = [['OPCODE', 'SEL_A', 'SEL_B'], ['OUT_NORTH', 'OUT_SOUTH', 'OUT_EAST', 'OUT_WEST']]

CONF_FIELDS = ["OUT_NORTH", "OUT_SOUTH", "OUT_EAST", "OUT_WEST", "OPCODE", "SEL_A", "SEL_B"]
SE_CONF_FORMAT_BIN = "{OUT_NORTH:03b}_{OUT_SOUTH:02b}_{OUT_EAST:03b}_{OUT_WEST:02b}"
ALU_CONF_FORMAT_BIN = "{OPCODE:04b}_{SEL_A:03b}_{SEL_B:03b}"
PE_CONF_FORMAT_BIN = "0" * 12 + "_" + SE_CONF_FORMAT_BIN + "_" + ALU_CONF_FORMAT_BIN
BITMAPS_BIN = "{rows[7]:01b}{rows[6]:01b}{rows[5]:01b}{rows[4]:01b}{rows[3]:01b}{rows[2]:01b}{rows[1]:01b}{rows[0]:01b}_" + \
                "{cols[11]:01b}{cols[10]:01b}{cols[9]:01b}{cols[8]:01b}{cols[7]:01b}{cols[6]:01b}" + \
                "{cols[5]:01b}{cols[4]:01b}{cols[3]:01b}{cols[2]:01b}{cols[1]:01b}{cols[0]:01b}"
ALU_RMC_FORMAT_BIN = "00_" + BITMAPS_BIN + "_" + ALU_CONF_FORMAT_BIN
SE_RMC_FORMAT_BIN = "00_" + BITMAPS_BIN + "_" + SE_CONF_FORMAT_BIN
PREG_CONF_FORMAT = "0" * 25 + "_" + "{6:01b}_{5:01b}_{4:01b}_{3:01b}_{2:01b}_{1:01b}_{0:01b}"

TABLE_FORMAT = "0000_0000_{5:04b}_{4:04b}_{3:04b}_{2:04b}_{1:04b}_{0:04b}"
TABLE_FORMER_OFFSET = 4
TABLE_LATTER_OFFSET = 8
TABLE_MASK_FORMAT = "0000_0000_0000_0000_0000_{11:01b}_{10:01b}_{9:01b}_{8:01b}" + \
                    "_{7:01b}_{6:01b}_{5:01b}_{4:01b}_{3:01b}_{2:01b}_{1:01b}_{0:01b}"
TABLE_MASK_OFFSET = 12


HEAD_FLIT = "001_{addr:022b}_{mt:03b}_{vch:03b}_{src:02b}_{dst:02b}\n"
TAIL_FLIT = "010_{data:s}\n"
MSG_TYPES = {"SW": 1}

class CCSOTB2_ConfGen(ConfGenBase):

    def __init__(self):
        # override style option setting
        self.style_types = {"llvm-ir": bool, "romultic": str, "duplicate": bool}
        self.style_choices = {"romultic": ["espresso", "ILP"]}
        self.style_default = {"llvm-ir": False, "romultic": None, "duplicate": False}

    def generate(self, header, data, individual_id, args):
        CGRA = header["arch"]
        individual = data["hof"][individual_id]
        app = header["app"]

        if CGRA.getArchName() != "CCSOTB2":
            raise TypeError("This solution is not for CCSOTB2, but for " + CGRA.getArchName())

        self.force_mode = args["force"]
        style_opt = self.style_args_parser(args["style"])

        # error in arguments
        if style_opt is None:
            return

        rmc_flag = not style_opt["romultic"] is None

        if os.path.exists(args["output_dir"]):
            # check export format
            if style_opt["llvm-ir"]:
                # check if llvmlite is avaiable
                try:
                    from ConfLLVMIR import ConfLLVMIR
                except ImportError:
                    print("Cannot import llvmlite. Please install it by \"pip3 install llvmlite\"")
                    return
                # set same name for file check later
                fig_save_enable = info_save_enable = False
                fig_filename = info_filename = ""
                conf_save_enable = True
                conf_filename = args["output_dir"] + "/" + args["prefix"] + "_conf.ll"
            else:
                fig_save_enable = info_save_enable = conf_save_enable = True
                fig_filename = args["output_dir"] + "/" + args["prefix"] + "_map.png"
                conf_filename = args["output_dir"] + "/" + args["prefix"] + "_conf.pkt"
                info_filename = args["output_dir"] + "/" + args["prefix"] + "_info.txt"

            # check if files exist
            files_exist = False
            if self.force_mode != True:
                files_exist |= (os.path.exists(fig_filename) & fig_save_enable)
                files_exist |= (os.path.exists(conf_filename) & conf_save_enable)
                files_exist |= (os.path.exists(info_filename) & info_save_enable)

            # mapping figure
            if files_exist:
                print("Cannot overwrite existing files")
            else:
                # make configurations
                PE_confs = self.make_PE_conf(CGRA, app, individual)
                ld_conf = self.make_LD_Dmanu(CGRA, individual.routed_graph)
                st_conf = self.make_ST_Dmanu(CGRA, individual.routed_graph)
                const_conf = self.make_Const(CGRA, individual.routed_graph)

                # enable multicasting
                if rmc_flag:
                    compressor = ConfCompressor(CGRA, CONF_FORMAT, PE_confs)
                    print("Now compressing configuration data....")
                    if style_opt["romultic"] == "espresso":
                        try:
                            rmc_confs = compressor.compress_espresso(RMC_PATTERN)
                        except RuntimeError as e:
                            print(e)
                            return
                    elif style_opt["romultic"] == "ILP":
                        rmc_confs = compressor.compress_coarse_grain_ILP(RMC_PATTERN)

                    print("Finish compressing: configuration data size", len(rmc_confs))

                dup_count = 1
                if style_opt["duplicate"]:
                    map_width = individual.getEvaluatedData("map_width")
                    if map_width is None:
                        print("duplicate option ignored because map width was not evaluated")
                    else:
                        dup_count = self.duplicate(CGRA, rmc_confs if rmc_flag else PE_confs,
                                                    ld_conf, st_conf, map_width, rmc_flag)

                if style_opt["llvm-ir"]:
                    ir_maker = ConfLLVMIR()
                    self.export_conf_llvmir(ir_maker, CGRA, rmc_confs if rmc_flag else PE_confs,\
                                            const_conf, ld_conf, st_conf, \
                                            individual.preg, dup_count, rmc_flag)
                    self.export_info_llvmir(ir_maker, header, individual, individual_id, ld_conf, st_conf)
                    with open(conf_filename, "w") as f:
                        f.writelines(ir_maker.get_IR())
                else:
                    self.save_conf(CGRA, rmc_confs if rmc_flag else PE_confs, const_conf, \
                                    ld_conf, st_conf, individual.preg, conf_filename, rmc_flag)

                if info_save_enable:
                    self.save_info(header, individual, individual_id, ld_conf, st_conf,\
                                    info_filename)

                if fig_save_enable:
                    try:
                        drawer = ConfDrawer(CGRA, individual)
                        drawer.draw_PEArray(CGRA, individual, app)
                        drawer.save(fig_filename)
                    except TclError as e:
                        print("Fail to save mapping figure because", e)
        else:
            print("No such direcotry: ", args["output_dir"])


    def export_conf_llvmir(self, IR_MAKER, CGRA, PE_confs, Const_conf, LD_conf,\
                             ST_conf, PREG_conf, DUPLICATE_COUNT, isRomultic):
        """exports configration data as LLVM IR

            Args:
                IR_MAKER (ConfLLVMIR)       : an instance of ConfLLVMIR
                CGRA (PEArrayModel)         : the target architecture
                PE_confs (dict of 2D list)  : configuration of each PE
                Const_conf (list)           : a list of const value
                LD_conf (dict)              : configuration of LD table
                ST_conf (dict)              : configuration of ST table
                PREG_conf (list of bool)    : flag of pipeline registers
                DUPLICATE_COUNT (int)       : count of mapping duplication
                isRomultic (bool)           : enable romultic
        """

        width, height = CGRA.getSize()

        # PE config
        pe_conf_pair = [[], []]
        se_rmc_conf = []
        alu_rmc_conf = []
        IR_MAKER.add_variable("__isRomultic", 1 if isRomultic else 0)
        if isRomultic:
            for entry in PE_confs:
                confs = {"rows": entry["rows"], "cols": entry["cols"]}
                confs.update(entry["conf"])
                if set(entry["conf"].keys()) == set(RMC_PATTERN[0]):
                    alu_rmc_conf.append(int(ALU_RMC_FORMAT_BIN.format(**confs), 2))
                else:
                    se_rmc_conf.append(int(SE_RMC_FORMAT_BIN.format(**confs), 2))

            IR_MAKER.add_array("__conf_alu_rmc", alu_rmc_conf)
            IR_MAKER.add_array("__conf_se_rmc", se_rmc_conf)
            # fill empty data
            IR_MAKER.add_array("__conf_addrs", [0])
            IR_MAKER.add_array("__conf_data", [0])
        else:
            for x in range(width):
                for y in range(height):
                    if len(PE_confs[x][y]) > 0:
                        addr = ((12 * y + x) * 0x200) + PE_CONF_BASEADDR
                        for filed in CONF_FIELDS:
                            if not filed in PE_confs[x][y]:
                                PE_confs[x][y][filed] = 0
                        pe_conf_pair[0].append(addr)
                        pe_conf_pair[1].append(int(PE_CONF_FORMAT_BIN.format(**PE_confs[x][y]), 2))
            IR_MAKER.add_array("__conf_addrs", pe_conf_pair[0])
            IR_MAKER.add_array("__conf_data", pe_conf_pair[1])
            # fill empty data
            IR_MAKER.add_array("__conf_alu_rmc", [0])
            IR_MAKER.add_array("__conf_se_rmc", [0])

        IR_MAKER.add_variable("__conf_len", len(pe_conf_pair[0]))
        IR_MAKER.add_variable("__alu_rmc_len", len(alu_rmc_conf))
        IR_MAKER.add_variable("__se_rmc_len", len(se_rmc_conf))

        # PREG Config
        if len(PREG_conf) == 0:
            PREG_conf = [False for i in range(7)]
        IR_MAKER.add_variable("__preg_conf", int(PREG_CONF_FORMAT.format(*PREG_conf), 2))

        # Const Regs
        const_arr = []
        for i in range(len(Const_conf)):
            int_const = int(Const_conf[i])
            if int_const < 0:
                int_const = 0x1FFFF + (int_const + 1) # converting 17-bit two's complement
            int_const &= 0x1FFFF
            const_arr.append(int_const)
        IR_MAKER.add_array("__const_data", const_arr)

        # LD table
        IR_MAKER.add_variable("__ld_table_former", \
                    int(TABLE_FORMAT.format(*LD_conf["table"][0:6]), 2))
        IR_MAKER.add_variable("__ld_table_latter", \
                    int(TABLE_FORMAT.format(*LD_conf["table"][6:12]), 2))
        IR_MAKER.add_variable("__ld_table_mask", \
                    int(TABLE_MASK_FORMAT.format(*LD_conf["mask"]), 2))

        # ST table
        IR_MAKER.add_variable("__st_table_former", \
                    int(TABLE_FORMAT.format(*ST_conf["table"][0:6]), 2))
        IR_MAKER.add_variable("__st_table_latter", \
                    int(TABLE_FORMAT.format(*ST_conf["table"][6:12]), 2))
        IR_MAKER.add_variable("__st_table_mask", \
                    int(TABLE_MASK_FORMAT.format(*ST_conf["mask"]), 2))

        # duplicate size
        IR_MAKER.add_variable("__duplicate_size", DUPLICATE_COUNT)

    def export_info_llvmir(self, IR_MAKER, header, individual, individual_id, LD_conf, ST_conf):
        """exports mapping information as LLVM IR

            Args:
                IR_MAKER (ConfLLVMIR)       : an instance of ConfLLVMIR
                header (dict)               : header of dumpfile
                individual (Individual)     : selected inidividual to be generated
                individual_id (int)         : ID of the selected individual
                LD_conf (dict)              : configuration of LD table
                ST_conf (dict)              : configuration of ST table
        """
        app = header["app"]
        sim_params = header["sim_params"]

        # save ID
        IR_MAKER.add_metadata("solution ID", individual_id)

        # save app name
        IR_MAKER.add_variable("__appname", app.getAppName())

        # save frequency
        IR_MAKER.add_metadata("Clock Frequncy", "{0}MHz".format(app.getFrequency("M")))

        # units setting
        IR_MAKER.add_metadata("Units setting", \
            "Time: " + sim_params.getTimeUnit() + \
            " Power: " + sim_params.getPowerUnit() + \
            " Energy: " + sim_params.getEnergyUnit())

        # evaluated data
        for eval_name, value in zip(header["eval_names"], individual.fitness.values):
            IR_MAKER.add_metadata(eval_name, value)

        # Other data
        leak = individual.getEvaluatedData("leakage_power")
        dynamic = individual.getEvaluatedData("dynamic_power")
        if not leak is None:
            IR_MAKER.add_metadata("Leakage Power", leak)

        if not dynamic is None:
            IR_MAKER.add_metadata("Dynamic Power", dynamic)

        body_bias = individual.getEvaluatedData("body_bias")
        if not body_bias is None:
            bb_data = ""
            for domain, voltage in body_bias.items():
                bb_data += "{0}: {1} V ".format(domain, voltage)
            IR_MAKER.add_metadata("Bias voltage", bb_data)

        # data memory alignment
        IR_MAKER.add_metadata("Input data alignment", LD_conf["mem_align"])
        IR_MAKER.add_metadata("Output data alignment", ST_conf["mem_align"])

    def save_conf(self, CGRA, PE_confs, Const_conf, LD_conf, ST_conf, PREG_conf, filename, isRomultic):
        """save configration data

            Args:
                CGRA (PEArrayModel)         : the target architecture
                PE_confs (dict of 2D list)  : configuration of each PE
                Const_conf (list)           : a list of const value
                LD_conf (dict)              : configuration of LD table
                ST_conf (dict)              : configuration of ST table
                PREG_conf (list of bool)    : flag of pipeline registers
                filename (str)              : filename to save the configration
                isRomultic (bool)           : enable romultic

            Returns:
                bool: whether the configration is saved successfully or not
        """

        f = open(filename, "w")
        width, height = CGRA.getSize()

        # PE config
        f.write("\n//PE Config\n")
        if isRomultic:
            for entry in PE_confs:
                confs = {"rows": entry["rows"], "cols": entry["cols"]}
                confs.update(entry["conf"])
                if set(entry["conf"].keys()) == set(RMC_PATTERN[0]):
                    # ALU multicasting
                    f.write(HEAD_FLIT.format(addr=ALU_RMC_ADDR, mt=MSG_TYPES["SW"], \
                                                    vch=0, src=0, dst=1))
                    f.write(TAIL_FLIT.format(data=ALU_RMC_FORMAT_BIN.format(**confs)))
                else:
                    # SE multicasting
                    f.write(HEAD_FLIT.format(addr=SE_RMC_ADDR, mt=MSG_TYPES["SW"], \
                                                    vch=0, src=0, dst=1))
                    f.write(TAIL_FLIT.format(data=SE_RMC_FORMAT_BIN.format(**confs)))
        else:
            for x in range(width):
                for y in range(height):
                    if len(PE_confs[x][y]) > 0:
                        addr = ((12 * y + x) * 0x200) + PE_CONF_BASEADDR
                        for filed in CONF_FIELDS:
                            if not filed in PE_confs[x][y]:
                                PE_confs[x][y][filed] = 0
                        f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                    vch=0, src=0, dst=1))
                        f.write(TAIL_FLIT.format(data=PE_CONF_FORMAT_BIN.format(**PE_confs[x][y])))

        # PREG Config
        if len(PREG_conf) == 0:
            PREG_conf = [False for i in range(7)]
        f.write("\n//PREG Config\n")
        addr = PREG_CONF_ADDR
        f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                    vch=0, src=0, dst=1))
        f.write(TAIL_FLIT.format(data=PREG_CONF_FORMAT.format(*PREG_conf)))

        # Const Regs
        f.write("\n//Const Regs\n")
        for i in range(len(Const_conf)):
            addr = CONST_BASEADDR + 4 * i
            f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                        vch=0, src=0, dst=1))
            int_const = int(Const_conf[i])
            if int_const < 0:
                int_const = 0x1FFFF + (int_const + 1) # converting 17-bit two's complement
            int_const &= 0x1FFFF
            f.write(TAIL_FLIT.format(data="{0:032b}".format(int_const)))

        # LD table
        f.write("\n//LD Table\n")
        addr = LD_DMANU_BASEADDR + TABLE_FORMER_OFFSET
        f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                vch=0, src=0, dst=1))
        f.write(TAIL_FLIT.format(data=TABLE_FORMAT.format(*LD_conf["table"][0:6])))

        addr = LD_DMANU_BASEADDR + TABLE_LATTER_OFFSET
        f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                vch=0, src=0, dst=1))
        f.write(TAIL_FLIT.format(data=TABLE_FORMAT.format(*LD_conf["table"][6:12])))


        addr = LD_DMANU_BASEADDR + TABLE_MASK_OFFSET
        f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                vch=0, src=0, dst=1))
        f.write(TAIL_FLIT.format(data=TABLE_MASK_FORMAT.format(*LD_conf["mask"])))


        # ST table
        f.write("\n//ST Table\n")
        addr = ST_DMANU_BASEADDR + TABLE_FORMER_OFFSET
        f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                vch=0, src=0, dst=1))
        f.write(TAIL_FLIT.format(data=TABLE_FORMAT.format(*ST_conf["table"][0:6])))

        addr = ST_DMANU_BASEADDR + TABLE_LATTER_OFFSET
        f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                vch=0, src=0, dst=1))
        f.write(TAIL_FLIT.format(data=TABLE_FORMAT.format(*ST_conf["table"][6:12])))


        addr = ST_DMANU_BASEADDR + TABLE_MASK_OFFSET
        f.write(HEAD_FLIT.format(addr=addr, mt=MSG_TYPES["SW"], \
                                                vch=0, src=0, dst=1))
        f.write(TAIL_FLIT.format(data=TABLE_MASK_FORMAT.format(*ST_conf["mask"])))

        f.close()

        return True

    def duplicate(self, CGRA, PE_confs, ld_conf, st_conf, map_width, isRomultic):
        """duplicate mapping horizontally
            Args:
                CGRA (PEArrayModel)                 : the target architecture
                PE_confs (dict of 2D list OR
                          list of dict (romultic) ) : configuration of each PE
                ld_conf (dict)                      : configuration of LD table
                st_conf (dict)                      : configuration of ST table
                map_width (int)                     : witdh of the mapping
                isRomultic (bool)                   : enabled romultic

            Returns:
                int: duplication count
        """
        width, height = CGRA.getSize()
        out_num = len(st_conf["mem_align"])
        in_num = len(ld_conf["mem_align"])
        dup_count = 0
        for dup_count in range(1, width // map_width):
            for x in range(map_width):
                dest_x = map_width * dup_count + x
                # LD table
                ld_conf["table"][dest_x] = ld_conf["table"][x] \
                                            + in_num * dup_count
                ld_conf["mask"][dest_x] = ld_conf["mask"][x]

                if isRomultic:
                    for entry in PE_confs:
                        entry["cols"][dest_x] = entry["cols"][x]
                else:
                    for y in range(height):
                        PE_confs[dest_x][y] = PE_confs[x][y]
            # ST table
            for out_idx in range(out_num):
                st_conf["table"][out_idx + dup_count * out_num] = st_conf["table"][out_idx] + map_width * dup_count
                st_conf["mask"][out_idx + dup_count * out_num] = st_conf["mask"][out_idx]


            # add in/out data
            for in_idx in range(in_num):
                ld_conf["mem_align"].append(ld_conf["mem_align"][in_idx] + "_(" + str(dup_count) + ")")
            for out_idx in range(out_num):
                st_conf["mem_align"].append(st_conf["mem_align"][out_idx] + "_(" + str(dup_count) + ")")

        return dup_count + 1

    def make_PE_conf(self, CGRA, app, individual):
        """analyzes PE configuration from mapping results
            Args:
                CGRA (PEArrayModel)         : the target architecture
                app (Application)           : the target application
                individual (Individual)     : selected inidividual to be generated

            Returns:
                dict of 2D list: configuration of each PE
                    key of the dict:    SE_OUTPUT's name or ALU fields
                    value of the dict:  configuration value

        """

        width, height = CGRA.getSize()

        comp_dfg = app.getCompSubGraph()

        routed_graph = individual.routed_graph

        confs = [ [ {} for y in range(height)] for x in range(width)]
        mux_name = {0: "SEL_A", 1: "SEL_B"}

        # ALUs
        for op_label, (x, y) in individual.mapping.items():
            if op_label in comp_dfg.nodes():
                opcode = comp_dfg.node[op_label]["opcode"]

            confs[x][y]["OPCODE"] = CGRA.getOpConfValue((x, y), opcode)
            alu = CGRA.get_PE_resources((x, y))["ALU"]
            pre_nodes = list(routed_graph.predecessors(alu))
            operands = {routed_graph.edges[(v, alu)]["operand"]: v \
                        for v in pre_nodes\
                        if "operand" in routed_graph.edges[(v, alu)]}
            mux_remain = set(mux_name.keys()) - set(operands.keys())
            for v in pre_nodes:
                if not v in operands.values():
                    operands[mux_remain.pop()] = v

            for k, v in operands.items():
                confs[x][y][mux_name[k]] = CGRA.getNetConfValue(alu, v)


        # routing ALU
        for x in range(width):
            for y in range(height):
                alu = CGRA.getNodeName("ALU", pos=(x,y))
                if alu in routed_graph.nodes():
                    if "route" in routed_graph.nodes[alu].keys():
                        if routed_graph.nodes[alu]["route"]:
                            opcode = CGRA.getRoutingOpcode(alu)
                            confs[x][y]["OPCODE"] = CGRA.getOpConfValue((x, y), opcode)
                            pre_node = list(routed_graph.predecessors(alu))[0]
                            confs[x][y]["SEL_A"] = confs[x][y]["SEL_B"] = \
                                CGRA.getNetConfValue(alu, pre_node)


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

    def make_LD_Dmanu(self, CGRA, routed_graph):
        """analyzes LD table from mapping results
            Args:
                CGRA (PEArrayModel)             : the target architecture
                routed_graph (networkx DiGraph) : routed graph on PE array resources

            Returns:
                dict: a generated table
                    keys and values
                    table       : transfer table
                    mask        : transfer mask
                    mem_align   : data alignment of input data

        """

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
        """analyzes ST table from mapping results
            Args:
                CGRA (PEArrayModel)             : the target architecture
                routed_graph (networkx DiGraph) : routed graph on PE array resources

            Returns:
                dict: a generated table
                    keys and values
                    table       : transfer table
                    mask        : transfer mask
                    mem_align   : data alignment of output data

        """

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
        """analyzes value of constant register from mapping results
            Args:
                CGRA (PEArrayModel)             : the target architecture
                routed_graph (networkx DiGraph) : routed graph on PE array resources

            Returns:
                list of int: const values
        """

        const_num = len(CGRA.getConstRegs())
        const_conf = [0 for i in range(const_num)]

        for i in range(const_num):
            c_reg = CGRA.getNodeName("Const", index=i)
            if c_reg in routed_graph.nodes():
                const_conf[i] = routed_graph.nodes[c_reg]["value"]

        return const_conf

    def save_info(self, header, individual, individual_id, LD_conf, ST_conf, filename):
        """save information data

            Args:
                header (dict)               : header of dumpfile
                individual (Individual)     : selected inidividual to be generated
                individual_id (int)         : ID of the selected individual
                LD_conf (dict)              : configuration of LD table
                ST_conf (dict)              : configuration of ST table
                filename (str)              : filename to save the configration

        """

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
    generator = CCSOTB2_ConfGen()
    generator.main()
