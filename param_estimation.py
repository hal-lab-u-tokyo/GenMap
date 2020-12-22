from PEArrayModel import PEArrayModel
from Application import Application
from Individual import Individual
from PowerEval import PowerEval
from SimParameters import SimParameters

import copy
from cmd import Cmd
import sys
import pickle
import os
import re
import readline
import csv
import math
from copy import copy
from argparse import ArgumentParser
import xml.etree.ElementTree as ET
from multiprocessing import Pool
import multiprocessing as multi

from scipy import optimize
import networkx as nx
from deap import base
from deap import creator

ERR_TH = 0.35


class MyShell(Cmd):
    prompt = "Param Estimator> "
    intro = "=== Parameter Estimation Utility ==="

    def __init__(self):
        Cmd.__init__(self)
        new_delims = readline.get_completer_delims()
        for c in "=!<>./-":
            new_delims = new_delims.replace(c, '')
        readline.set_completer_delims(new_delims)
        self.__dumplist = []
        self.__resultlist = []
        self.__target_arch = None
        self.__exec_flag = False
        self.__energy_unit = "pJ"
        self.__op_sw_opt_rate = 0.0

    def do_EOF(self, arg):
        print()
        return self.do_quit(arg)

    def emptyline(self):
        pass

    def do_set_unit(self, line):
        args = line.split(" ")
        args = [argv for argv in args if argv != ""]

        if len(args) == 1:
            if args[0] in ["pJ", "nJ", "uJ", "mJ"]:
                self.__energy_unit = args[0]
            else:
                print("invalid unit for energy:", args[0])
        else:
            self.help_set_unit()

    def help_set_unit(self):
        print("usage: set_unit (pJ|nJ|uJ|mJ)")
        print("\t\tspecify energy unit of input data (default: pJ)")

    def do_input_data(self, line):
        args = line.split(" ")
        args = [argv for argv in args if argv != ""]
        if len(args) < 2:
            self.help_input_data()
            return
        if os.access(args[0], os.R_OK):
            if os.access(args[1], os.R_OK):
                self.__dumplist.append(args[0])
                self.__resultlist.append(args[1])
            else:
                print("cannot read", args[1])
        else:
            print("cannot read", args[0])


    def help_input_data(self):
        print("usage: input_data dumpfile csvfile")

    def complete_input_data(self, text, line, begidx, endidx):
        args = line.split(" ")
        args = [argv for argv in args if argv != ""]

        if text == "":
            args.append("")
        # check positional args
        file_postfix = None
        if len(args) == 2:
            file_postfix = "dump"
        elif len(args) == 3:
            file_postfix = "csv"

        return self.__get_file_list(args, text, file_postfix)

    def do_set_arch(self, line):
        args = line.split(" ")
        args = [argv for argv in args if argv != ""]
        if len(args) == 0:
            self.help_set_arch()
            return
        else:
            if os.access(args[0], os.R_OK):
                # parse XML file
                try:
                    tree_arch = ET.ElementTree(file=args[0])
                except ET.ParseError as e:
                    print("Parse Error ({0})".format(args[0]), e.args, file=sys.stderr)
                    return
                if tree_arch.getroot().tag == "PEArray":
                    # make model instance
                    try:
                        self.__target_arch = PEArrayModel(tree_arch.getroot())
                    except (ValueError, PEArrayModel.InvalidConfigError) as e:
                        print("Invalid definition", e.args)
                        return
                else:
                    print("Parse Error ({0})".format(args[0]), \
                            "\nRoot tag name must be \"PEArray\"", file=sys.stderr)
                    return
            else:
                print("No such file: " + args[0], file=sys.stderr)
                return

    def help_set_arch(self):
        print("usage: set_arch arch_description.xml")

    def complete_set_arch(self, text, line, begidx, endidx):
        args = line.split(" ")
        args = [argv for argv in args if argv != ""]

        if text == "":
            args.append("")
        # check positional args
        file_postfix = None
        if len(args) == 2:
            file_postfix = "xml"
        return self.__get_file_list(args, text, file_postfix)

    def __get_file_list(self, args, text, file_postfix):

        if not file_postfix is None:
            if text[-2:] == "..":
                text += "/"
            pos = text.rfind("/")
            if pos != -1:
                # extract & scan upper directories
                dir_name = text[:pos+1]
                remains = text[pos+1:]
                files = os.scandir(dir_name)
            else:
                # scam current dir
                dir_name = ""
                remains = text
                files = os.scandir()


            comp_args = [dir_name + f.name + ("/" if f.is_dir() else " ")\
                        for f in files if (f.is_dir() and f.name.startswith(remains)) or \
                        (f.name.startswith(remains) and f.name.endswith(file_postfix))]

            return comp_args

    def do_execute(self, line):
        parsed_args = self.parse_execute([argv for argv in line.split(" ") if argv != ""])
        if not parsed_args is None:
            if len(self.__dumplist) > 0:
                self.__exec_flag = True
                self.__op_sw_opt_rate = parsed_args.op_sw_opt
                return True
            else:
                print("At least, one input data is specified")

    def parse_execute(self, args):
        usage = "execute [--op-sw-opt rate(float)]\nIt executes parameter estimation"
        parser = ArgumentParser(prog = "execute", usage=usage)
        parser.add_argument("--op-sw-opt", type=float, default=0.0)

        try:
            parsed_args = parser.parse_args(args=args)
        except SystemExit:
            return None

        return parsed_args

    def help_execute(self):
        self.parse_execute(["-h"])

    def get_files(self):
        return [(d, c) for d, c in zip(self.__dumplist, self.__resultlist) ]

    def do_quit(self, _):
        print("Exiting the shell...")
        return True

    def help_quit(self):
        print("usage: quit\nExits the shell")

    def isExecute(self):
        return self.__exec_flag

    def getTargetArch(self):
        return self.__target_arch

    def getUnit(self):
        return self.__energy_unit

    def getOpSwOptRate(self):
        return self.__op_sw_opt_rate

def mt_wrapper(args):
    (CGRA, sim_params, c) = args
    return abs(c["real"] - PowerEval.eval_glitch(CGRA, c["app"], sim_params, c["ind"])) / c["real"]

def cost_func(params, cases, CGRA, sim_params):
    print(params)
    sim_params.switching_energy = params[0]
    sim_params.switching_propagation = params[1]
    sim_params.switching_decay = params[2]
    sim_params.se_weight = params[3]

    errs = [0.0 for i in range(len(cases))]

    if len([v for v in params if v < 0]) > 0:
        return [10000000000 for i in range(len(cases))]

    p = Pool(multi.cpu_count())
    mt_args = [(CGRA, sim_params, cases[i]) for i in range(len(cases))]
    errs = p.map(mt_wrapper, mt_args)
    p.close()

    # single process ver
    # for i in range(len(cases)):
    #     errs[i] = (abs(cases[i]["real"] - PowerEval.eval_glitch(CGRA, cases[i]["app"], sim_params, cases[i]["ind"])) \
    #                     / cases[i]["real"])

    return errs

def cost_func2(params, cases, CGRA, sim_params, original_sw, weight):
    for k, i in zip(sorted(sim_params.switching_info), range(len(params))):
        sim_params.switching_info[k] = original_sw[i] * (1 + weight * math.tanh(params[i]))
    print(["{0:.3f}".format(v) for v in sim_params.switching_info.values()])
    errs = [0.0 for i in range(len(cases))]

    for i in range(len(cases)):
        errs[i] = (abs(cases[i]["real"] - PowerEval.eval_glitch(CGRA, cases[i]["app"], sim_params, cases[i]["ind"])) \
                        / cases[i]["real"])

    return errs

if __name__ == "__main__":

    shell = MyShell()

    # start Shell
    while (1):
        try:
            shell.cmdloop()
            break
        except KeyboardInterrupt:
            shell.intro = ""
            print()
            continue

    if not shell.isExecute():
        sys.exit()

    # prepare for loading result data
    creator.create("Fitness", base.Fitness, weights=(1))
    creator.create("Individual", Individual, fitness=creator.Fitness)

    header_list = []
    data_list = []
    real_value_list = []
    # load all files
    for dump_file, result_file in shell.get_files():
        # load dump file
        with open(dump_file, "rb") as f:
            try:
                header_list.append(pickle.load(f))
                data_list.append(pickle.load(f))
            except EOFError:
                print("Invalid dumpfile: ", dump_file)
                sys.exit()
        # load result file
        with open(result_file, "r") as f:
            reader = csv.reader(f)
            # skip header
            header = next(reader)
            real_value_list.append([row for row in reader])
        # validate both file
        if len(data_list[-1]["hof"]) != len(real_value_list[-1]):
            print(dump_file, "and", result_file, "are not compatible")
            sys.exit()

    arch_set = set([head["arch"].getArchName() for head in header_list])
    if len(arch_set) > 1:
        print("Different architecture dumps are used", arch_set)
        sys.exit()
    elif not shell.getTargetArch() is None and \
            list(arch_set)[0] != shell.getTargetArch().getArchName():
        print("Different architecture between specified({0}) one and dumps({1})".format(
                    shell.getTargetArch().getArchName(), list(arch_set)[0]))
        sys.exit()

    # get some instances from first dump
    if shell.getTargetArch() is None:
        model = header_list[0]["arch"]
    else:
        model = shell.getTargetArch()
    sim_params = header_list[0]["sim_params"]

    # set initial parameters
    params = [0.1, 1., 1., 0.8,]

    # set cases
    cases = []
    preg_num = model.getPregNumber()
    preg_bin_str = "{0:0" + str(preg_num) + "b}"
    for head, data, real in zip(header_list, data_list, real_value_list):
        for i in range(len(data["hof"])):
            if preg_num == 0:
                if real[i][0] != "null" and real[i][0] != "":
                    f_value = float(real[i][0])
                    cases.append({"ind": data["hof"][i], "app": head["app"], "real": f_value})
            else:
                for preg in range(min(len(real[i]), 2**preg_num)):
                    if real[i][preg] != "null" and real[i][preg] != "":
                        f_value = float(real[i][preg])
                        cases.append({"ind": copy(data["hof"][i]), "app": head["app"], "real": f_value})
                        cases[-1]["ind"].preg = [f == "1" for f in preg_bin_str.format(preg)[::-1]]
                        print(head["app"].getAppName(), "ID: ", i, "preg:", preg, "is applied real value", f_value)

    print("Sample count: ", len(cases))

    sim_params.change_unit_scale("energy", shell.getUnit())


    result = optimize.least_squares(cost_func, params, \
             args=(cases, model, sim_params), method="lm")

    if result["success"]:
        print("Estimation was finished successfully")
        print("status", result["status"])
    else:
        print("Fail to Estimation")
        sys.exit()

    params = result["x"]
    print("Estimated parameters")
    print("switching energy", params[0])
    print("switching propagation", params[1])
    print("switching decay", params[2])
    print("se weight", params[3])


    # updated by estmiated params
    sim_params.switching_energy = params[0]
    sim_params.switching_propagation = params[1]
    sim_params.switching_decay = params[2]
    sim_params.se_weight = params[3]

    # second stage
    if shell.getOpSwOptRate() != 0.0:
        print("Running op switching count optimization")
        weight = shell.getOpSwOptRate()
        original_sw = [sim_params.switching_info[k] for k in sorted(sim_params.switching_info)]
        params = [0 for i in original_sw]
        
        result = optimize.least_squares(cost_func2, params, \
                                        args=(cases, model, sim_params, original_sw, weight), method="lm")

        if result["success"]:
            print("Estimatino was finished successfully")
            print("status", result["status"])
        else:
            print("Fail to Estimation")
            sys.exit()

        params = result["x"]
        print("Estimated parameters", params)
        # updated by estimated params
        for k, i in zip(sorted(sim_params.switching_info), range(len(original_sw))):
            sim_params.switching_info[k] = original_sw[i] * ( 1 + weight * math.tanh(params[i]))

        print(sim_params.switching_info)
    

    sim = [0 for i in range(len(cases))]
    errs = [0 for i in range(len(cases))]

    over_errs = []
    for i in range(len(cases)):
        sim[i] = PowerEval.eval_glitch(model, cases[i]["app"], sim_params, cases[i]["ind"])
        errs[i] = abs(cases[i]["real"] - sim[i])/ cases[i]["real"]
        if errs[i] > ERR_TH:
            over_errs.append(i)

    min_err = min(errs)
    min_case = errs.index(min_err)
    max_err = max(errs)
    max_case = errs.index(max_err)

    print("Report")
    print("seq\tmodel sim\treal\t\terror")
    for i in range(len(sim)):
        print("{0:3d}\t{1:8.10f}\t{2:2.2f}\t\t{3:2.2f}%\t\t{4}".format(i, sim[i], cases[i]["real"], errs[i] * 100,\
            "lager" if sim[i] - cases[i]["real"] > 0 else "smaller"))
    print("ME=", sum([errs[i] for i in range(len(errs)) if not i in over_errs]) / (len(errs) - len(over_errs)) * 100, "%")
    print("over errs: ", len(over_errs))
    print("Min=", min_err * 100, "%", "case:", min_case, cases[min_case]["real"])
    print("Max=", max_err * 100, "%", "case:", max_case, cases[max_case]["real"])
    print("Median=", sorted(errs)[len(errs) // 2] * 100, "%") 


