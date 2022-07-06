#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

from operator import index
import os
import json
import math
import sys
from argparse import ArgumentParser
from importlib import import_module

from networkx.algorithms.core import k_core

from ConfGenBase import ConfGenBase
from ConfDrawer import ConfDrawer

from MapHeightEval import MapHeightEval
from MapWidthEval import MapWidthEval
from LatencyBalanceEval import LatencyBalanceEval
from EvalBase import EvalBase

import matplotlib
import warnings

from PEArrayModel import PEArrayModel
from PEArrayModel import CONST_node_exp
warnings.filterwarnings('ignore', category=matplotlib.MatplotlibDeprecationWarning)

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns
from tkinter import TclError


class Generic_ConfGen(ConfGenBase):

    def __init__(self):
        # override style option setting
        self.style_types = {"v_duplicate": bool, "h_duplicate": bool, \
                            "readable": bool, "origin": str}
        self.style_default = {"v_duplicate": False, "h_duplicate": False, \
                                "readable": False, "origin": "bottom-left"}
        self.style_choices = {"origin": ["bottom-left", "top-left",\
                                             "bottom-right", "top-right"]}
        self.extra_eval = set()
        self.lat_analysis_en = False

    # override parser
    def parser(self):
        usage = 'Usage: python3 {0} optimization_result'.format(self.__class__.__name__ + ".py")
        argparser = ArgumentParser(usage=usage)
        argparser.add_argument("result", type=str, help="optimization result")
        argparser.add_argument("--eval", nargs="*", action="store", type=str, \
                                help="report additional evaluation result")
        argparser.add_argument("--enable-latency-analysis", action="store_true", \
                                help="enables latency analysis and creates report files")
        argparser.set_defaults(eval=[])
        args = argparser.parse_args()
        self.make_eval_instance(set(args.eval))
        self.lat_analysis_en = args.enable_latency_analysis
        return args

    def make_eval_instance(self, eval_list):
        for eval_name in eval_list:
            try:
                evl = getattr(import_module(eval_name), eval_name)
            except ModuleNotFoundError:
                print("Import Error for an objective: " + eval_name)
                sys.exit(1)
            if not issubclass(evl, EvalBase):
                print(evl.__name__ + " is not EvalBase class")
                sys.exit(1)
            self.extra_eval.add(evl)

    def generate(self, header, data, individual_id, args):
        CGRA = header["arch"]
        individual = data["hof"][individual_id]
        app = header["app"]
        sim_params = header["sim_params"]

        self.force_mode = args["force"]
        style_opt = self.style_args_parser(args["style"])

        # error in arguments
        if style_opt is None:
            return

        if os.path.exists(args["output_dir"]):
            # export the conf file as binary file
            file_list = dict()
            file_list["map"] = args["output_dir"] + "/" + \
                                args["prefix"] + "_map.png"
            file_list["conf"] = args["output_dir"] + "/" + args["prefix"] + \
                                    "_conf.json"

            if self.lat_analysis_en:
                file_list["hist"] = args["output_dir"] + "/" + \
                                    args["prefix"] + "_latency_hist.png"
                file_list["heat"] = args["output_dir"] + "/" + \
                                    args["prefix"] + "_latency_heat.png"

            # check if any files already exist
            files_exist = False
            if self.force_mode != True:
                for f in file_list.values():
                    if os.path.exists(f):
                        files_exist = True
                        break

            # mapping figure
            if files_exist:
                print("Cannot overwrite existing files")
            else:
                # get arch & mapping info
                conf = {"info": self.make_info(header, \
                                    individual, individual_id)}
                # get configurations
                conf["PE"] = self.get_PE_conf(CGRA, app, individual, \
                                            style_opt["readable"])
                # get memory port configurations
                conf["memory"] = self.make_mem_conf(CGRA, \
                                            individual.routed_graph,\
                                            style_opt["readable"])
                # get const reg configurations
                if not CGRA.isIOShared():
                    conf["const"] = self.make_Const(CGRA,\
                                         individual.routed_graph)

                # dup_count = 1
                map_height = MapHeightEval.eval(CGRA, app, sim_params,\
                                                    individual)
                map_width = MapWidthEval.eval(CGRA, app, sim_params,\
                                                    individual)
                # if style_opt["duplicate"]:
                #     dup_count = self.duplicate(CGRA, PE_confs, AG_confs,\
                #                                     map_height)

                # save as json
                with open(file_list["conf"], mode="wt", encoding="utf-8") as f:
                    json.dump(conf, f, ensure_ascii=False, indent=2)

                # save mapping fig
                try:
                    drawer = ConfDrawer(CGRA, individual, style_opt["origin"])
                    drawer.draw_PEArray(CGRA, individual, app)
                    drawer.save(file_list["map"])
                except TclError as e:
                    print("Fail to save mapping figure because", e)

                size = (map_width, map_height)
                if self.lat_analysis_en:
                    try:
                        self.save_latency_analysis(CGRA, app, sim_params, individual, size,\
                                                        file_list["hist"],\
                                                        file_list["heat"],\
                                                        style_opt["origin"])
                    except TclError as e:
                        print("Fail to save latency analysis graph because", e)

        else:
            print("No such direcotry: ", args["output_dir"])

    def save_latency_analysis(self, CGRA,  app, sim_params, ind, size, hist_file_name,\
                                heat_file_name, origin):
        """save latency analysis result
            Args:
                CGRA (PEArrayModel)         : the target architecture
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for some simulations
                individual (Individual)     : selected inidividual to be generated
                size (tuple)                : width x height to create heatmap
                hist_file_name (str)        : file name for
                                                latency diffrence histgram
                heat_file_name (str)        : file name for
                                                latency diffrence heatmap
                origin (str): position of coordinate origin
                    available values are following:
                        "bottom-left", "top-left", "bottom-right", "top-right"

            Returns: None

        """
        latency_diff = ind.getEvaluatedData("latency_diff")
        if latency_diff is None:
            # not evaluated
            LatencyBalanceEval.eval(CGRA, app, sim_params, ind)
            latency_diff = ind.getEvaluatedData("latency_diff")

        lat_rng = [i for i in range(math.floor(min(latency_diff.values())), \
                    math.ceil(max(latency_diff.values())) + 1)]

        node_count = {i: 0 for i in lat_rng}
        for k, v in latency_diff.items():
            node_count[round(v)] += 1

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
        if origin in ["top-right", "bottom-right"]:
            xtick = xtick[::-1]
        ytick = list(range(height))
        if origin in ["bottom-left", "bottom-right"]:
            ytick = ytick[::-1]
        mask = [ [ True for x in range(width) ] for y in range(height)]
        lat = [ [ 0 for x in range(width) ] for y in range(height)]
        for x in range(width):
            for y in range(height):
                alu = CGRA.getNodeName("ALU", pos = (xtick[x], ytick[y]))
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


    # def duplicate(self, CGRA, PE_confs, AG_confs, map_height):
    #     """duplicate mapping horizontally
    #         Args:
    #             CGRA (PEArrayModel)                 : the target architecture
    #             PE_confs (dict of 2D list: configuration of each PE
    #             AG_confs (dict of dict):
    #                 key: coord of AGs
    #                 values: configuration of AGs (dict)
    #             map_height (int)                    : height of the mapping

    #         Returns:
    #             int: duplication count
    #     """
    #     width, height = CGRA.getSize()
    #     # assuming left/right-most Tiles are AGs
    #     map_height = max(max([y for (_, y) in AG_confs.keys()]), map_height)

    #     for dup_count in range(1, height // map_height):
    #         for y in range(map_height):
    #             dest_y = map_height * dup_count + y
    #             for x in range(width):
    #                 PE_confs[x][dest_y] = copy.copy(PE_confs[x][y])
    #                 PE_conf[x][dest_y]["label"] += "_" + str(dup_count)

    #             if (0, y) in AG_confs.keys():
    #                 AG_confs[(0, dest_y)] = copy.copy(AG_confs[(0, y)])
    #                 AG_confs[(0, dest_y)]["label"] += "_" + str(dup_count)
    #             if (width, y) in AG_confs.keys():
    #                 AG_confs[(width, dest_y)] = copy.copy(AG_confs[(width, y)])
    #                 AG_confs[(width, dest_y)]["label"] += "_" + str(dup_count)


    #     return dup_count + 1

    def get_PE_conf(self, CGRA, app, individual, readable):
        """analyzes PE configuration from mapping results
            Args:
                CGRA (PEArrayModel)         : the target architecture
                app (Application)           : the target application
                individual (Individual)     : selected inidividual to be generated
                readable (bool)             : if true, save the configuration
                                                data as with readable format
                                                instead of raw value
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

        save_opcode = (lambda pos, opcode : CGRA.getOpConfValue(pos, opcode)) \
                        if not readable else \
                            (lambda _, opcode : opcode)
        save_net_conf = (lambda dst, src : CGRA.getNetConfValue(dst, src)) \
                        if not readable else \
                            (lambda _, src : src)


        # ALUs
        for op_label, (x, y) in individual.mapping.items():
            # get opcode
            if op_label in comp_dfg.nodes():
                opcode = comp_dfg.node[op_label]["opcode"]
            confs[x][y]["label"] = op_label
            confs[x][y]["opcode"] = save_opcode((x, y), opcode)
            alu = CGRA.get_PE_resources((x, y))["ALU"]
            # get mux sel
            mux_count = CGRA.getALUMuxCount((x, y))
            mux_remain = set(range(mux_count))
            pre_nodes = list(routed_graph.predecessors(alu))
            operands = {routed_graph.edges[(v, alu)]["operand"]: v \
                        for v in pre_nodes\
                        if "operand" in routed_graph.edges[(v, alu)]}
            mux_remain -= set(operands.keys())

            # set imm
            const_reg = []
            if not CGRA.isNeedConstRoute():
                imm_list = []
                if op_label in const_dfg.nodes():
                    for pre_c in const_dfg.predecessors(op_label):
                        imm_list.append(app.getConstValue(pre_c))
                        sel = const_dfg.edges[(pre_c, op_label)]["operand"]
                        c_node = CONST_node_exp.format(index=\
                                                len(imm_list) - 1)
                        const_reg.append(c_node)
                        if not sel is None:
                            operands[sel] = c_node
                            mux_remain.remove(sel)
                        else:
                            pre_nodes.append(c_node)
                confs[x][y]["imm"] = imm_list

            # assign muxs for dont care inputs
            for v in pre_nodes:
                if not v in operands.values():
                    operands[mux_remain.pop()] = v
            for v in mux_remain:
                operands[v] = None

            # store mux sel signals
            confs[x][y]["mux"] = [save_net_conf(alu, v) \
                                        for _, v in sorted(operands.items(),
                                        key=lambda x: x[0])]
            confs[x][y]["imm_sel"] = [ const_reg.index(v)\
                                        if v in const_reg else None \
                                        for _, v in sorted(operands.items(),
                                        key=lambda x: x[0])]

        # routing ALU
        for x in range(width):
            for y in range(height):
                alu = CGRA.getNodeName("ALU", pos=(x,y))
                if alu in routed_graph.nodes():
                    if "route" in routed_graph.nodes[alu].keys():
                        if routed_graph.nodes[alu]["route"]:
                            opcode = CGRA.getRoutingOpcode(alu)
                            confs[x][y]["opcode"] = save_opcode((x, y), opcode)
                            confs[x][y]["label"] = "ROUTE"
                            confs[x][y]["imm"] = []
                            pre_node = list(routed_graph.predecessors(alu))[0]
                            confs[x][y]["mux"] = \
                                [ save_net_conf(alu, pre_node) \
                                    for _ in range(mux_count) ]
                            confs[x][y]["imm_sel"] = [None for _ in range(mux_count)]


        # SEs
        for x in range(width):
            for y in range(height):
                se_conf = {}
                se_conf_val = {}
                se_list = CGRA.get_PE_resources((x, y))["SE"]
                # for each SE outputs
                for se_id, se_set in se_list.items():
                    connection = {}
                    for se in se_set:
                        if se in routed_graph.nodes():
                            pre_node = list(routed_graph.predecessors(se))[0]
                            connection[se] = pre_node
                    if len(connection) > 0:
                        se_conf[se_id] = {CGRA.getWireName(k): \
                                            save_net_conf(k, v) \
                                            for k, v in connection.items()}

                if len(se_conf) > 0:
                    confs[x][y]["SE"] = se_conf

        return confs


    def make_mem_conf(self, CGRA, routed_graph, readable):
        """exracts memory access configuration
            Args:
                CGRA (PEArrayModel)             : the target architecture
                routed_graph (networkx DiGraph) : routed graph on PE array resources
                readable (bool)             : if true, save the configuration
                                                data as with readable format
                                                instead of raw value

            Returns:
                For IO shared PE arch:
                    list: info about used IO port
                For the others:
                    dict:
                        key and value:
                            "load": info about used input port
                            "store" info about used output port
        """
        w, h = CGRA.getSize()

        mem_loads = [i for i in CGRA.getInputPorts() \
                        if i in routed_graph.nodes()]
        mem_stores = [o for o in CGRA.getOutputPorts() \
                        if o in routed_graph.nodes()]

        isize = len(CGRA.getInputPorts())
        osize = len(CGRA.getOutputPorts())

        load_conf = [{} for _ in range(isize)]
        store_conf = [{} for _ in range(osize)]

        for i in range(isize):
            inode = CGRA.getNodeName("IN_PORT", index = i)
            if inode in mem_loads:
                load_conf[i]["label"] = routed_graph.nodes[inode]["map"]


        for i in range(osize):
            onode = CGRA.getNodeName("OUT_PORT", index = i)
            if onode in mem_stores:
                pre_node = list(routed_graph.predecessors(onode))[0]
                if readable:
                    sel = pre_node
                else:
                    sel = CGRA.getNetConfValue(onode, pre_node)

                store_conf[i] = {"label": routed_graph.nodes[onode]["map"],
                        "mux": sel}


        if CGRA.isIOShared():
            mem_conf = []
            for i in range(isize):
                if len(load_conf[i]) > 0:
                    mem_conf.append({"mode": "load"})
                    mem_conf[-1].update(load_conf[i])
                elif len(store_conf[i]) > 0:
                    mem_conf.append({"mode": "store"})
                    mem_conf[-1].update(store_conf[i])
                else:
                    mem_conf.append({})
        else:
            mem_conf = {"load": load_conf, "store": store_conf}

        return mem_conf

    def make_Const(self, CGRA, routed_graph):
        """analyzes value of constant register from mapping results
            Args:
                CGRA (PEArrayModel)             : the target architecture
                routed_graph (networkx DiGraph) : routed graph on PE array resources

            Returns:
                list of int: const values
                            if the const reg is not used, its value is None
        """

        const_num = len(CGRA.getConstRegs())
        const_conf = [None for i in range(const_num)]

        for i in range(const_num):
            c_reg = CGRA.getNodeName("Const", index=i)
            if c_reg in routed_graph.nodes():
                const_conf[i] = routed_graph.nodes[c_reg]["value"]

        return const_conf

    def make_info(self, header, individual, individual_id):
        """make information data for json

            Args:
                header (dict)               : header of dumpfile
                individual (Individual)     : selected inidividual to be generated
                individual_id (int)         : ID of the selected individual

            Returns:
                dict:
                    key and value:
                        "arch": dict of architecture info
                        "mapping": dict of mapping info
        """
        CGRA : PEArrayModel = header["arch"]
        app = header["app"]
        sim_params = header["sim_params"]

        # arch info
        arch_info = {}
        arch_info["name"] = CGRA.getArchName()
        arch_info["size"] = CGRA.getSize()
        IOShared = CGRA.isIOShared()
        arch_info["IOShared"] = IOShared
        arch_info["const_reg_num"] = len(CGRA.getConstRegs())
        if IOShared:
            arch_info["mem_io_size"] = len(CGRA.getInoutPorts())
        else:
            arch_info["mem_load_size"] = len(CGRA.getInputPorts())
            arch_info["mem_store_size"] = len(CGRA.getInputPorts())

        # IO pos info
        pos_list = ["left", "right", "bottom", "top"]
        ip_pos = {pos: [] for pos in pos_list}
        op_pos = {pos: [] for pos in pos_list}
        isize = len(CGRA.getInputPorts())
        osize = len(CGRA.getOutputPorts())
        iport_node2index = {CGRA.getNodeName("IN_PORT", index=i):i for i in range(isize)}
        oport_node2index = {CGRA.getNodeName("OUT_PORT", index=i):i for i in range(osize)}

        for pos in pos_list:
            for ip in CGRA.getInputPortsByPos(pos):
                ip_pos[pos].append(iport_node2index[ip])
            for op in CGRA.getOutputPortsByPos(pos):
                op_pos[pos].append(oport_node2index[op])
        if CGRA.isIOShared():
            pos_info = {k: v for k, v in ip_pos.items() if len(v) > 0}
        else:
            pos_info = {"load": {k: v for k, v in ip_pos.items() if len(v) > 0},
                        "store": {k: v for k, v in op_pos.items() if len(v) > 0}}
        arch_info["mem_pos"] = pos_info

        # mapping info
        mapping_info = {}
        # target clock
        mapping_info["Target Clock Frequency"] = app.getFrequency("M")
        # unit setting
        unit_info = {}
        unit_info["Time"] = sim_params.getTimeUnit()
        unit_info["Power"] = sim_params.getPowerUnit()
        unit_info["Energy"] = sim_params.getEnergyUnit()
        mapping_info["Units setting"] = unit_info

        # extracted ID
        mapping_info["solution ID"] = str(individual_id)

        # app
        mapping_info["app name"] = app.getAppName()

        # evaluated data
        eval_res = {}
        for eval_name, value in zip(header["eval_names"], individual.fitness.values):
            eval_res[eval_name] = value

        eval_res.update(individual.getAllEvaluatedData().items())

        # get extra evaluation
        for objective in self.extra_eval:
            if not objective.name() in eval_res:
                eval_res[objective.name()] = \
                        objective.eval(CGRA, app, sim_params, individual)
                

        mapping_info["Evaluation results"] = eval_res

        return {"arch": arch_info, "mapping": mapping_info}


if __name__ == '__main__':
    generator = Generic_ConfGen()
    generator.main()
