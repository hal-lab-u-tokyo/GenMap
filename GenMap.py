#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

# GenMap classes
from PEArrayModel import PEArrayModel
from Application import Application
from SimParameters import SimParameters
from Placer import Placer
from Individual import Individual
from NSGA2 import NSGA2

# standard libs
from argparse import ArgumentParser
import sys
import termios
import os
import time
import pickle
import xml.etree.ElementTree as ET
from datetime import datetime

def parser():
    usage = 'Usage: python3 {0} [options...] dot_file frequency'.format(__file__)
    argparser = ArgumentParser(usage=usage)
    argparser.add_argument("dot_file", type=str, help="application data-flow-graph")
    argparser.add_argument("--freq", type=float, help='operation frequency', default=1.0)
    argparser.add_argument("-o", "--output", type=str, \
                            help="specify the output file name(default = {app_name}.dump")
    argparser.add_argument("--arch", type=str, help="specify architecure definition file " + \
                            "(default = arch.xml)",
                            default="arch.xml")
    argparser.add_argument("--opt-conf", type=str, help="specify optimization parameter configuration file " + \
                            "(default = OptimizationParameters.xml)", \
                            default="OptimizationParameters.xml")
    argparser.add_argument("--simdata", type=str, help="specify simulation data file" + \
                            "(default = simdata.xml)", \
                            default="simdata.xml")
    argparser.add_argument("--init-map", type=str, help="specify mapping initilizing method" + \
                            "(default = graphviz)", \
                            default="graphviz", choices=["graphviz", "tsort", "random"])
    argparser.add_argument("--freq-unit", type=str, choices=["M", "G", "k"], default="M",\
                            help="specify the prefix of frequency unit (default = M)")
    argparser.add_argument("--log", type=str, help="specify log file name (default: no logging)")
    argparser.add_argument("--nproc", type=int, help="specify the number of multi-process (default: cpu count)")
    argparser.add_argument("--data-flow", type=str, \
                            help="specify the data flow direction", \
                            choices=Placer.DATA_FLOW.keys(), default="any")
    args = argparser.parse_args()
    return args

def checkFeasibility(CGRA, app):
    comp_dfg = app.getCompSubGraph()
    need_ops = {op: 0 for op in CGRA.getSupportedOps()}
    w, h = CGRA.getSize()
    if len(comp_dfg.nodes()) > w * h:
        print("The size of PE array is {0}x{1} " + \
                    "but DFG contains {2} nodes".format(\
                    w, h, len(comp_dfg.nodes)))

    for v in comp_dfg.nodes():
        op = comp_dfg.nodes[v]["opcode"]
        if op in need_ops:
            need_ops[op] += 1
        else:
            print("operation: {0} does not supported in {1}".format(\
                    op, CGRA.getArchName()))
            return False

    for k, v in need_ops.items():
        if len(CGRA.getSupportedALUs(k)) < v:
            print("No enough PE for {0} in {1}".format(k, \
                    CGRA.getArchName()))
            return False

    return True

if __name__ == '__main__':

    launch_msg = """
# ==================================================
#       ____            __  __             
#      / ___| ___ _ __ |  \/  | __ _ _ __  
#     | |  _ / _ \ '_ \| |\/| |/ _` | '_ \ 
#     | |_| |  __/ | | | |  | | (_| | |_) |
#      \____|\___|_| |_|_|  |_|\__,_| .__/ 
#                                   |_|   
# ==================================================

    Copyright (c) 2021 Amano laboratory, Keio University
    Launching... PID: {0}
    """.format(os.getpid())

    print(launch_msg)
    args = parser()

    # load application dot file
    app = Application()
    if os.path.exists(args.dot_file):
        if app.read_dot(args.dot_file) == False:
            exit()
        app.setFrequency(args.freq, args.freq_unit)
    else:
        print("No such file: " + args.dot_file, file=sys.stderr)
        exit()

    # load architecture definition
    if os.path.exists(args.arch):
        # parse XML file
        try:
            tree_arch = ET.ElementTree(file=args.arch)
        except ET.ParseError as e:
            print("Parse Error ({0})".format(args.arch), e.args, file=sys.stderr)
            exit()

        if tree_arch.getroot().tag == "PEArray":
            # make model instance
            try:
                model = PEArrayModel(tree_arch.getroot())
            except (ValueError, PEArrayModel.InvalidConfigError) as e:
                print("Invalid definition", e.args)
                exit()
        else:
            print("Parse Error ({0})".format(args.arch), \
                    "\nRoot tag name must be \"PEArray\"", file=sys.stderr)
            exit()
    else:
        print("No such file: " + args.arch, file=sys.stderr)
        exit()

    # load simluation data
    if os.path.exists(args.simdata):
        # parse XML file
        try:
            tree_sim = ET.ElementTree(file=args.simdata)
        except ET.ParseError as e:
            print("Parse Error ({0})".format(args.simdata), e.args, file=sys.stderr)
            exit()
        # make simParameters instance
        try:
            sim_params = SimParameters(model, tree_sim.getroot())
        except SimParameters.InvalidParameters as e:
            print("Parameter import failed: ", e.args)
            exit()
    else:
        print("No such file: " + args.simdata, file=sys.stderr)
        exit()

    # check logging option
    if not args.log is None:
        if os.path.exists(args.log):
            # add postfix
            logfile_name = args.log + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        else:
            logfile_name = args.log
        # open and create
        logfile = open(logfile_name, "w")
    else:
        logfile = None

    # check output file
    if args.output is None:
        output_file_name = app.getAppName() + ".dump"
    else:
        output_file_name = args.output
        # check if output dir exists
        output_dir = os.path.dirname(output_file_name)
        if output_dir != "":
            if not os.path.exists(output_dir):
                print("output directory:", output_dir, "does not exist")
                exit()

    # confirm overwite
    if os.path.exists(output_file_name):
        inp=input('overwrite ' + output_file_name + ' y/n? >> ')=='y'
        if inp == False:
            exit()

    # check feasibility of this application for the archtecture
    if not checkFeasibility(model, app):
        exit()

    # load optimization setting
    if os.path.exists(args.opt_conf):
        # parse XML file
        try:
            tree_opt = ET.ElementTree(file=args.opt_conf)
        except ET.ParseError as e:
            print("Parse Error ({0})".format(args.opt_conf), e.args, file=sys.stderr)
            exit()
        # make optimizer
        try:
            optimizer = NSGA2(tree_opt.getroot(), logfile=logfile)
        except (ValueError, TypeError) as e:
            print("Config import failed: ", e.args[0])
            exit()
    else:
        print("No such file: " + args.opt_conf, file=sys.stderr)
        exit()

    if not args.nproc is None:
        success_setup = optimizer.setup(model, app, sim_params, args.init_map,\
                            args.data_flow, proc_num = args.nproc)
    else:
        success_setup = optimizer.setup(model, app, sim_params, args.init_map,\
                                            args.data_flow)

    # run optimization
    if success_setup:
        # tty echo off
        if sys.stdin.isatty():
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            new = termios.tcgetattr(fd)
            new[3] &= ~(termios.ECHO | termios.ICANON)
            tty_off = True
        else:
            tty_off = False

        start_time = time.time()

        try:
            if tty_off:
                termios.tcsetattr(fd, termios.TCSANOW, new)
            hof, fitness_log = optimizer.runOptimization()
            elapsed_time = time.time() - start_time
            time_msg = "elapsed time: {0} [sec]".format(elapsed_time)
            print(time_msg)
            if not logfile is None:
                logfile.write(time_msg + "\n")
        except KeyboardInterrupt:
            # exit safety
            if tty_off:
                termios.tcsetattr(fd, termios.TCSANOW, old)
            if not logfile is None:
                logfile.close()
            sys.exit()
        finally:
            if tty_off:
                # discard std input
                print("Please enter any keys\n")
                _ = sys.stdin.read(1)
                # restore tty attr
                termios.tcsetattr(fd, termios.TCSANOW, old)

        # save results
        objectives = optimizer.getObjectives()
        save_header = {"app": app, "arch": model, "opt_conf": tree_opt.getroot(),
                        "sim_params": sim_params,
                        "eval_names": [obj.name() for obj in objectives],
                        "fitness_weights": tuple(-1.0 if obj.isMinimize() else 1.0 for obj in objectives)}
        save_data = {"hof": hof, "fitness_log": fitness_log}

        print("Saving optimization results...")
        with open(output_file_name, "wb") as file:
            pickle.dump(save_header, file)
            pickle.dump(save_data, file)

    else:
        print("Fail to initilize")

    if not logfile is None:
        logfile.close()

