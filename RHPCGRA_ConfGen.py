#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

import os
import struct
import copy

from ConfGenBase import ConfGenBase
from ConfDrawer import ConfDrawer

from MapHeightEval import MapHeightEval
from MapWidthEval import MapWidthEval
from LatencyBalanceEval import LatencyBalanceEval

import matplotlib
import warnings
warnings.filterwarnings('ignore', category=matplotlib.MatplotlibDeprecationWarning)

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns
from tkinter import TclError

COMP_FMT = "confTILE({x}, {y}, {IMM[0]}, {OPCODE}, {IMM_EN}, " + \
            "{IMM_SEL}, {MUX1}, {MUX2}); //{label} \n"
AG_FMT = "confAGloop2({x}, {y}, {OPCODE}, {MUX1}, %%STARTX%%, %%ENDX%%, %%INCX%%, %%STARTY%%, %%ENDY%%, %%INCY%%); //{label}\n"

class RHPCGRA_ConfGen(ConfGenBase):

    def __init__(self):
        # override style option setting
        self.style_types = {"llvm-ir": bool, "duplicate": bool, "simd": int }
        self.style_default = {"llvm-ir": False, "duplicate": False, "simd": 1}

    def generate(self, header, data, individual_id, args):
        CGRA = header["arch"]
        individual = data["hof"][individual_id]
        app = header["app"]
        sim_params = header["sim_params"]

        if not CGRA.getArchName().startswith("RHP-CGRA"):
            raise TypeError("This solution is not for RHP-CGRA, but for " + CGRA.getArchName())

        self.force_mode = args["force"]
        style_opt = self.style_args_parser(args["style"])

        # error in arguments
        if style_opt is None:
            return

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
                fig_save_enable = info_save_enable = \
                    lat_anal_save_enable = False
                fig_filename = info_filename = lat_anal_filename = ""
                conf_save_enable = True
                conf_filename = args["output_dir"] + "/" + args["prefix"] + "_conf.ll"
            else:
                # export the conf file as binary file
                fig_save_enable = info_save_enable = \
                    conf_save_enable = lat_anal_save_enable = True
                fig_filename = args["output_dir"] + "/" + args["prefix"] + "_map.png"
                conf_filename = args["output_dir"] + "/" + args["prefix"] + "_conf.txt"
                info_filename = args["output_dir"] + "/" + args["prefix"] + "_info.txt"
                lat_anal_hist_filename = args["output_dir"] + "/" + \
                                        args["prefix"] + "_latency_hist.png"
                lat_anal_heat_filename = args["output_dir"] + "/" + \
                                        args["prefix"] + "_latency_heat.png"

            # check if files exist
            files_exist = False
            if self.force_mode != True:
                files_exist |= (os.path.exists(fig_filename) & fig_save_enable)
                files_exist |= (os.path.exists(conf_filename) & conf_save_enable)
                files_exist |= (os.path.exists(info_filename) & info_save_enable)
                files_exist |= (os.path.exists(lat_anal_hist_filename) & lat_anal_save_enable)
                files_exist |= (os.path.exists(lat_anal_heat_filename) & lat_anal_save_enable)

            # mapping figure
            if files_exist:
                print("Cannot overwrite existing files")
            else:
                # make configurations
                try:
                    PE_confs = self.make_PE_conf(CGRA, app, individual)
                    AG_confs = self.make_AG_conf(CGRA, individual.routed_graph)
                except TypeError as e:
                    print(e)
                    return

                dup_count = 1
                map_height = MapHeightEval.eval(CGRA, app, sim_params,\
                                                    individual)
                map_width = MapWidthEval.eval(CGRA, app, sim_params,\
                                                    individual)
                if style_opt["duplicate"]:
                    dup_count = self.duplicate(CGRA, PE_confs, AG_confs,\
                                                    map_height)

                if style_opt["llvm-ir"]:
                    print("Export in LLVM-IR is not implemented yet")
                    # ir_maker = ConfLLVMIR()
                    # self.export_conf_llvmir(ir_maker, CGRA, rmc_confs if rmc_flag else PE_confs,\
                    #                         const_conf, ld_conf, st_conf, \
                    #                         individual.preg, dup_count, rmc_flag)
                    # self.export_info_llvmir(ir_maker, header, individual, individual_id, ld_conf, st_conf)
                    # with open(conf_filename, "w") as f:
                    #     f.writelines(ir_maker.get_IR())
                else:
                    self.save_conf(CGRA, PE_confs, AG_confs, conf_filename)

                if info_save_enable:
                    self.save_info(header, individual, individual_id,\
                                    info_filename)

                if fig_save_enable:
                    try:
                        drawer = ConfDrawer(CGRA, individual)
                        drawer.draw_PEArray(CGRA, individual, app)
                        drawer.save(fig_filename)
                    except TclError as e:
                        print("Fail to save mapping figure because", e)

                if lat_anal_save_enable:
                    size = (map_width, map_height)
                    try:
                        self.save_latency_analysis(CGRA, individual, size,\
                                                      lat_anal_hist_filename,\
                                                      lat_anal_heat_filename)
                    except TclError as e:
                        print("Fail to save latency analysis graph because", e)

        else:
            print("No such direcotry: ", args["output_dir"])

    def save_latency_analysis(self, CGRA, ind, size, hist_file_name,\
                                heat_file_name):
        """save latency analysis result
            Args:
                CGRA (PEArrayModel)         : the target architecture
                individual (Individual)     : selected inidividual to be generated
                size (tuple)                : width x height to create heatmap
                hist_file_name (str)        : file name for
                                                latency diffrence histgram
                heat_file_name (str)        : file name for
                                                latency diffrence heatmap

            Returns: None

        """
        latency_diff = ind.getEvaluatedData("latency_diff")
        if latency_diff is None:
            # not evaluated
            latency_diff = LatencyBalanceEval.analyze_latency_diff(CGRA, ind)

        lat_rng = [i for i in range(min(latency_diff.values()), \
                    max(latency_diff.values()) + 1)]
        node_count = {i: 0 for i in lat_rng}
        for k, v in latency_diff.items():
            node_count[v] += 1

        fig, ax = plt.subplots()
        ax.get_yaxis().set_major_locator(ticker.MaxNLocator(integer=True))
        ax.bar(lat_rng, list(node_count.values()), \
                tick_label = lat_rng)
        ax.set_ylabel("# of nodes")
        ax.set_xlabel("Difference of latency")
        fig.tight_layout()
        plt.savefig(hist_file_name)

        # create heatmap
        fig = plt.figure()
        width, height = size
        xtick = list(range(width))
        ytick = list(range(height))[::-1]
        mask = [ [ True for x in range(width) ] for y in range(height)]
        lat = [ [ 0 for x in range(width) ] for y in range(height)]
        for x in range(width):
            for y in range(height):
                alu = CGRA.getNodeName("ALU", pos = (x, ytick[y]))
                if alu in latency_diff.keys():
                    lat[y][x] = latency_diff[alu]
                    mask[y][x] = False

        lat = np.array(lat)
        mask = np.array(mask)
        sns.heatmap(lat, cbar = False, cmap = "binary", linewidths=1)
        sns.heatmap(lat, cmap="Reds", mask = mask, linewidths=1,\
                     linecolor="black", xticklabels=xtick, \
                     yticklabels=ytick, annot=True, vmin=0)
        plt.savefig(heat_file_name)


    def save_conf(self, CGRA, PE_confs, AG_confs, filename):
        f = open(filename, "w")
        w, h = CGRA.getSize()

        for x in range(w):
            for y in range(h):
                if len(PE_confs[x][y]) > 0:
                    conf = PE_confs[x][y]
                    if "IMM" in conf:
                        conf["IMM_EN"] = 1
                    else:
                        conf["IMM"] = [0]
                        conf["IMM_SEL"] = 0
                        conf["IMM_EN"] = 0
                    if not "MUX2" in conf:
                        conf["MUX2"] = 0
                    # left-most tile are AGs, so x is incremented by 1
                    f.write(COMP_FMT.format(x = x + 1, y = y, **conf))

        for coord, conf in AG_confs.items():
            conf["OPCODE"] = 0 if conf["mode"] == "load" else 1
            conf["x"], conf["y"] = coord
            f.write(AG_FMT.format(**conf))
        f.close()


    def duplicate(self, CGRA, PE_confs, AG_confs, map_height):
        """duplicate mapping horizontally
            Args:
                CGRA (PEArrayModel)                 : the target architecture
                PE_confs (dict of 2D list: configuration of each PE
                AG_confs (dict of dict):
                    key: coord of AGs
                    values: configuration of AGs (dict)
                map_height (int)                    : height of the mapping

            Returns:
                int: duplication count
        """
        width, height = CGRA.getSize()
        # assuming left/right-most Tiles are AGs
        map_height = max(max([y for (_, y) in AG_confs.keys()]), map_height)

        for dup_count in range(1, height // map_height):
            for y in range(map_height):
                dest_y = map_height * dup_count + y
                for x in range(width):
                    PE_confs[x][dest_y] = copy.copy(PE_confs[x][y])
                    PE_conf[x][dest_y]["label"] += "_" + str(dup_count)

                if (0, y) in AG_confs.keys():
                    AG_confs[(0, dest_y)] = copy.copy(AG_confs[(0, y)])
                    AG_confs[(0, dest_y)]["label"] += "_" + str(dup_count)
                if (width, y) in AG_confs.keys():
                    AG_confs[(width, dest_y)] = copy.copy(AG_confs[(width, y)])
                    AG_confs[(width, dest_y)]["label"] += "_" + str(dup_count)


        return dup_count + 1

    def make_PE_conf(self, CGRA, app, individual):
        """analyzes PE configuration from mapping results
            Args:
                CGRA (PEArrayModel)         : the target architecture
                app (Application)           : the target application
                individual (Individual)     : selected inidividual to be generated

            Returns:
                dict of 2D list: configuration of each PE
                    key of the dict: keywords correspond to the format
                    value of the dict:  configuration value

        """

        width, height = CGRA.getSize()

        comp_dfg = app.getCompSubGraph()
        const_dfg = app.getConstSubGraph()

        routed_graph = individual.routed_graph

        confs = [ [ {} for y in range(height)] for x in range(width)]

        # ALUs
        for op_label, (x, y) in individual.mapping.items():
            if op_label in comp_dfg.nodes():
                opcode = comp_dfg.node[op_label]["op"]
            confs[x][y]["OPCODE"] = CGRA.getOpConfValue((x, y), opcode)
            confs[x][y]["label"] = op_label
            alu = CGRA.get_PE_resources((x, y))["ALU"]
            pre_nodes = list(routed_graph.predecessors(alu))
            operands = {routed_graph.edges[(v, alu)]["operand"]: v \
                        for v in pre_nodes\
                        if "operand" in routed_graph.edges[(v, alu)]}

            if "left" in operands and "right" in operands:
                confs[x][y]["MUX1"] = CGRA.getNetConfValue(alu, operands["left"])
                confs[x][y]["MUX2"] = CGRA.getNetConfValue(alu, operands["right"])
            elif "left" in operands:
                confs[x][y]["MUX1"] = CGRA.getNetConfValue(alu, operands["left"])
                pre_nodes.remove(operands["left"])
                if len(pre_nodes) > 0:
                    confs[x][y]["MUX2"] = CGRA.getNetConfValue(alu, pre_nodes[0])
            elif "right" in operands:
                confs[x][y]["MUX2"] = CGRA.getNetConfValue(alu, operands["right"])
                pre_nodes.remove(operands["right"])
                if len(pre_nodes) > 0:
                    confs[x][y]["MUX1"] = CGRA.getNetConfValue(alu, pre_nodes[0])
            else:
                if len(pre_nodes) > 0:
                    confs[x][y]["MUX1"] = CGRA.getNetConfValue(alu, pre_nodes[0])
                if len(pre_nodes) > 1:
                    confs[x][y]["MUX2"] = CGRA.getNetConfValue(alu, pre_nodes[1])

            # set imm
            if op_label in const_dfg.nodes():
                for pre_c in const_dfg.predecessors(op_label):
                    c_type_str = const_dfg.nodes[pre_c]["const"]
                    if c_type_str == "float":
                        try:
                            c_value = float(pre_c)
                        except ValueError:
                            raise TypeError(pre_c + " is not float number")
                    else:
                        try:
                            c_value = int(pre_c)
                        except ValueError:
                            raise TypeError(pre_c + " is not interger")
                    confs[x][y]["IMM"] = [pre_c]
                    try:
                        sel = const_dfg.edges[(pre_c, op_label)]["operand"]
                        if sel == "left":
                            if "MUX1" in confs[x][y]:
                                print("Warning: duplicated left operand for",\
                                        op_label)
                            confs[x][y]["IMM_SEL"] = 0
                            confs[x][y]["MUX1"] = 0
                        else:
                            if "MUX2" in confs[x][y]:
                                print("Warning: duplicated right operand for",\
                                        op_label)
                            confs[x][y]["IMM_SEL"] = 1
                            confs[x][y]["MUX2"] = 0

                    except KeyError:
                        confs[x][y]["IMM_SEL"] = 0 if "MUX2" else 1


        # routing ALU
        for x in range(width):
            for y in range(height):
                alu = CGRA.getNodeName("ALU", pos=(x,y))
                if alu in routed_graph.nodes():
                    if "route" in routed_graph.nodes[alu].keys():
                        if routed_graph.nodes[alu]["route"]:
                            opcode = CGRA.getRoutingOpcode(alu)
                            confs[x][y]["OPCODE"] = CGRA.getOpConfValue((x, y), opcode)
                            confs[x][y]["label"] = "ROUTE"
                            pre_node = list(routed_graph.predecessors(alu))[0]
                            confs[x][y]["MUX1"] = confs[x][y]["MUX2"] = \
                                CGRA.getNetConfValue(alu, pre_node)


        # # SEs
        # for x in range(width):
        #     for y in range(height):
        #         se_list = CGRA.get_PE_resources((x, y))["SE"]
        #         if len(se_list) == 1:
        #             # for each SE outputs
        #             for se in list(se_list.values())[0]:
        #                 if se in routed_graph.nodes():
        #                     pre_node = list(routed_graph.predecessors(se))[0]
        #                     confs[x][y][CGRA.getWireName(se)] = CGRA.getNetConfValue(se, pre_node)
        #         else:
        #             raise TypeError("CCSOTB2 assumes one SE per PE")

        return confs


    def make_AG_conf(self, CGRA, routed_graph):
        """exracts AG configuration
            Args:
                CGRA (PEArrayModel)             : the target architecture
                routed_graph (networkx DiGraph) : routed graph on PE array resources

            Returns:
                dict: info about the used AGs
                        keys: coords of the used AGs
                        values: dict of conf
                            keys:
                                mode: modes of AGs (load or store)
                                label: corresponding node name in the DFG
        """
        w, h = CGRA.getSize()
        load_AGs = [i for i in CGRA.getInputPorts() \
                        if i in routed_graph.nodes()]
        store_AGs = [o for o in CGRA.getOutputPorts() \
                        if o in routed_graph.nodes()]

        isize = len(CGRA.getInputPorts())
        osize = len(CGRA.getOutputPorts())

        AG_conf = {}

        for i in range(isize):
            inode = CGRA.getNodeName("IN_PORT", index = i)
            if not inode in load_AGs:
                continue
            # assuming left/right-most Tiles are AGs
            if i < h:
                # left side
                coord = (0, i)
            else:
                # right side
                coord = (w, i - h)
            AG_conf[coord] = {"mode": "load", \
                    "label": routed_graph.nodes[inode]["map"], "MUX1": 0}

        for i in range(osize):
            onode = CGRA.getNodeName("OUT_PORT", index = i)
            if not onode in store_AGs:
                continue
            # assuming left/right-most Tiles are AGs
            if i < h:
                # left side
                coord = (0, i)
            else:
                # right side
                coord = (w, i - h)
            pre_node = list(routed_graph.predecessors(onode))[0]
            sel = CGRA.getNetConfValue(onode, pre_node)

            AG_conf[coord] = {"mode": "store", \
                    "label": routed_graph.nodes[onode]["map"],
                    "MUX1": sel}

        return AG_conf

    def save_info(self, header, individual, individual_id, filename):
        """save information data

            Args:
                header (dict)               : header of dumpfile
                individual (Individual)     : selected inidividual to be generated
                individual_id (int)         : ID of the selected individual
                filename (str)              : filename to save the configration

        """

        app = header["app"]

        f = open(filename, "w")
        # save ID
        f.write("ID: " + str(individual_id) + "\n\n")

        # save app name
        f.write("APP: " + app.getAppName() + "\n\n")

        # evaluated data
        f.write("Evaluation results\n")
        for eval_name, value in zip(header["eval_names"], individual.fitness.values):
            f.write("{0}: {1}\n".format(eval_name, value))

        f.close()



if __name__ == '__main__':
    generator = RHPCGRA_ConfGen()
    generator.main()
