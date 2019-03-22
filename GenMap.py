
# GenMap classes
from PEArrayModel import PEArrayModel
from Application import Application
from SimParameters import SimParameters
from Placer import Placer
from Individual import Individual
from NSGA2 import NSGA2

# Router
from AStarRouter import AStarRouter

# optimization objectives
from WireLengthEval import WireLengthEval
from MapWidthEval import MapWidthEval
from PowerEval import PowerEval
from OpMapWidthEval import OpMapWidthEval
from TimeSlackEval import TimeSlackEval

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
    argparser.add_argument("freq", type=float, help='operation frequency')
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
    argparser.add_argument("--duplicate-enable",  action='store_true', \
                            help="enable duplication of data-flow mapping horizontally")
    argparser.add_argument("--freq-unit", type=str, choices=["M", "G", "k"], default="M",\
                            help="specify the prefex of frequency prefex (default = M)")
    argparser.add_argument("--log", type=str, help="specify log file name (default: no logging)")
    argparser.add_argument("--nproc", type=int, help="specify the number of multi-process (default: cpu count)")
    args = argparser.parse_args()
    return args

if __name__ == '__main__':
    args = parser()

    # load application dot file
    app = Application()
    if os.path.exists(args.dot_file):
        app.read_dot(args.dot_file)
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

    # confirm overwite
    if os.path.exists(output_file_name):
        inp=input('overwrite ' + output_file_name + ' y/n? >> ')=='y'
        if inp == False:
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
        except SimParameters.InvalidParameters as e:
            print("Parameter import failed: ", e.args)
    else:
        print("No such file: " + args.opt_conf, file=sys.stderr)
        exit()

    # setup optimization
    objectives = [WireLengthEval, MapWidthEval, OpMapWidthEval, PowerEval, TimeSlackEval]

    if not args.nproc is None:
        success_setup = optimizer.setup(model, app, sim_params, AStarRouter, objectives,\
                        [{}, {}, {}, {"duplicate_enable": args.duplicate_enable}, {}], \
                        proc_num = args.nproc)
    else:
        success_setup = optimizer.setup(model, app, sim_params, AStarRouter, objectives,\
                        [{}, {}, {}, {"duplicate_enable": args.duplicate_enable}, {}])

    # run optimization
    if success_setup:
        # tty echo off
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        new[3] &= ~(termios.ECHO | termios.ICANON)

        start_time = time.time()

        try:
            termios.tcsetattr(fd, termios.TCSANOW, new)
            hof, hv = optimizer.runOptimization()
            elapsed_time = time.time() - start_time
            print("elapsed time:", elapsed_time, "[sec]")
        except KeyboardInterrupt:
            # exit safety
            termios.tcsetattr(fd, termios.TCSANOW, old)
            if not logfile is None:
                logfile.close()
            sys.exit()
        finally:
            # discard std input
            print("Please enter any keys\n")
            _ = sys.stdin.read(1)
            # restore tty attr
            termios.tcsetattr(fd, termios.TCSANOW, old)

        # save results
        save_header = {"app": app, "arch": model, "opt_conf": tree_opt.getroot(),
                        "sim_params": sim_params,
                        "eval_names": [obj.name() for obj in objectives],
                        "fitness_weights": tuple(-1.0 if obj.isMinimize() else 1.0 for obj in objectives)}
        save_data = {"hof": hof, "hypervolume": hv}

        print("Saving optimization results...")
        with open(output_file_name, "wb") as file:
            pickle.dump(save_header, file)
            pickle.dump(save_data, file)

    else:
        print("Fail to initilize")

    if not logfile is None:
        logfile.close()

