from cmd import Cmd
from argparse import ArgumentParser
import prettytable
import copy
import readline
import os
import csv
import re

from ConfDrawer import ConfDrawer



class GenMapShell(Cmd):
    prompt = "GenMap shell> "
    intro = "=== GenMap solution selection utility ==="

    def __init__(self, header, data, conf_gen):
        Cmd.__init__(self)
        self.header = header
        self.data = data
        self.filtered_sols = list(copy.deepcopy(self.data["hof"]))
        new_delims = readline.get_completer_delims()
        for c in "=!<>./-":
            new_delims = new_delims.replace(c, '')
        readline.set_completer_delims(new_delims)
        self.selected_id = -1
        self.conf_gen = conf_gen

        # check hypervolume is available
        self.__hv_enable = True
        try:
            from pygmo.core import hypervolume
            self.hypervolume = hypervolume
        except ImportError:
            self.__hv_enable = False

    def do_EOF(self, arg):
        print()
        return self.do_quit(arg)

    def emptyline(self):
        pass

    def do_show(self, _):
        head = ["ID"]
        head.extend(self.header["eval_names"])
        table = prettytable.PrettyTable(head)
        for ind in self.filtered_sols:
            row = [list(self.data["hof"]).index(ind)]
            row.extend(list(ind.fitness.values))
            table.add_row(row)
        print(table)

    def help_show(self):
        print("usage: show\nIt shows filtered solutions")

    def do_sort(self, line):
        parsed_args = self.parse_sort(line.split(" "))

        if not parsed_args is None:
            obj_idx = self.header["eval_names"].index(parsed_args.object)

            if parsed_args.order == "asc" or \
                parsed_args.order == "ASC":
                self.filtered_sols = sorted(self.filtered_sols, \
                                        key=lambda x: x.fitness.values[obj_idx])
            else:
                self.filtered_sols = sorted(self.filtered_sols, \
                                        key=lambda x: - x.fitness.values[obj_idx])

    def complete_sort(self, text, line, begidx, endidx):
        args = line.split(" ")
        args = [argv for argv in args if argv != ""]
        if text == "":
            args.append(text)

        pos = args.index(text)

        if pos == 1:
            comp_args = [obj for obj in self.header["eval_names"] if obj.startswith(text)]
        elif pos == 2:
            comp_args = [order for order in ["asc", "desc", "ASC", "DESC"] \
                            if order.startswith(text)]
        else:
            comp_args = []

        return comp_args


    def help_sort(self):
        self.parse_sort(["--help"])

    def parse_sort(self, args):
        usage = "sort {0} {1}\nIt sorts filtered solutions".format(\
                    self.__bold_font("objective"), self.__bold_font("order"))
        parser = ArgumentParser(prog = "sort", usage=usage)
        parser.add_argument("object", type=str, choices=self.header["eval_names"])
        parser.add_argument("order", type=str, choices=["asc", "desc", "ASC", "DESC"])

        try:
            parsed_args = parser.parse_args(args=args)
        except SystemExit:
            return None

        return parsed_args


    def do_filter(self, line):
        parsed_args = self.parse_filter(line.split(" "))

        if not parsed_args is None:
            obj_idx = self.header["eval_names"].index(parsed_args.object)

            if parsed_args.comp_operator == "==":
                self.filtered_sols = [ind for ind in self.filtered_sols\
                                        if ind.fitness.values[obj_idx] == \
                                        parsed_args.value]
            elif parsed_args.comp_operator == "!=":
                self.filtered_sols = [ind for ind in self.filtered_sols\
                                        if ind.fitness.values[obj_idx] != \
                                        parsed_args.value]
            elif parsed_args.comp_operator == "<":
                self.filtered_sols = [ind for ind in self.filtered_sols\
                                        if ind.fitness.values[obj_idx] < \
                                        parsed_args.value]
            elif parsed_args.comp_operator == ">":
                self.filtered_sols = [ind for ind in self.filtered_sols\
                                        if ind.fitness.values[obj_idx] > \
                                        parsed_args.value]
            elif parsed_args.comp_operator == "<=":
                self.filtered_sols = [ind for ind in self.filtered_sols\
                                        if ind.fitness.values[obj_idx] <= \
                                        parsed_args.value]
            else:
                self.filtered_sols = [ind for ind in self.filtered_sols\
                                        if ind.fitness.values[obj_idx] >= \
                                        parsed_args.value]

    def complete_filter(self, text, line, begidx, endidx):
        args = line.split(" ")
        args = [argv for argv in args if argv != ""]
        if text == "":
            args.append(text)

        pos = args.index(text)

        if pos == 1:
            comp_args = [obj for obj in self.header["eval_names"] if obj.startswith(text)]
        elif pos == 2:
            comp_args = [op for op in ["==", "!=", "<", ">", "<=", ">="] \
                            if op.startswith(text)]
        else:
            comp_args = []

        return comp_args

    def help_filter(self):
        self.parse_filter(["--help"])

    def parse_filter(self, args):
        usage = "filter {0} {1} {2}\nIt filters solutions with a condition".format(\
                self.__bold_font("objective"), \
                self.__bold_font("comp_operator"),\
                self.__bold_font("value"))
        parser = ArgumentParser(prog = "filter", usage=usage)
        parser.add_argument("object", type=str, choices=self.header["eval_names"])
        parser.add_argument("comp_operator", type=str, \
                            choices=["==", "!=", "<", ">", "<=", ">="])
        parser.add_argument("value", type=float)

        try:
            parsed_args = parser.parse_args(args=args)
        except SystemExit:
            return None

        return parsed_args

    def do_reset(self, _):
        self.filtered_sols = list(copy.deepcopy(self.data["hof"]))
        self.selected_id = -1

    def help_reset(self):
        print("usage: reset\nIt resets filtering and selected ID")

    def do_quit(self, _):
        print("Exiting the shell...")
        return True

    def help_quit(self):
        print("usage: quit\nExits the shell")

    def do_select(self, line):
        args = line.split(" ")
        if len(args) != 1:
            self.help_select()
        else:
            try:
                if args[0] == "-":
                    # select the top solution
                    sol_id = list(self.data["hof"]).index(self.filtered_sols[0])
                else:
                    sol_id = int(args[0])
            except ValueError:
                print("select: {0} is not integer value".format(args[0]))
                return;
            except IndexError:
                print("select: no solution satisfying condition(s)")
                return
            if sol_id >= len(self.data["hof"]):
                print("select: ID {0}  is out of range".format(args[0]))
            else:
                self.selected_id = sol_id

    def help_select(self):
        print("usage: select {0}\nIt selects a solution".format(\
            self.__bold_font("solution_ID")))

    def do_view(self, _):
        if self.selected_id < 0:
            print("view: a solution is not selected")
        else:
            model = self.header["arch"]
            ind = self.data["hof"][self.selected_id]
            app = self.header["app"]
            drawer = ConfDrawer(model, ind)
            drawer.draw_PEArray(model, ind, app)
            drawer.show()

    def help_view(self):
        print("usage: view\nIt visualizes the selected solution")

    def do_save(self, line):
        parsed_args = self.parse_save(line.split(" "))

        if not parsed_args is None:
            if self.selected_id < 0:
                print("save: a solution is not selected")
            else:
                try:
                    self.conf_gen.generate(self.header, self.data,\
                                         self.selected_id, vars(parsed_args))
                except TypeError as e:
                    print(e)

    def parse_save(self, args):
        usage = "save [options...]\nIt generates configuration files of selected solutions"
        parser = ArgumentParser(prog = "save", usage=usage)
        parser.add_argument("-o", "--output_dir", type=str, \
                            help="specify output directory name",\
                            default=self.header["app"].getAppName())
        parser.add_argument("-f", "--force", action='store_true', \
                            help="overwrite without prompt")
        parser.add_argument("-p", "--prefix", type=str, \
                            help="specify prefix of output file names (default: app_name)",\
                            default=self.header["app"].getAppName())
        parser.add_argument("-s", "--style", nargs="+", default=[],\
                            help="Pass the space separated arguments to configuration generator")

        try:
            parsed_args = parser.parse_args(args=[argv for argv in args if argv != ""])
        except SystemExit:
            return None

        return parsed_args

    def complete_save(self, text, line, begidx, endidx):
        args = line.split(" ")
        args = [argv for argv in args if argv != ""]
        if text == "":
            args.append("")

        # in case of output option, complete file/directory names
        if len(args) > 0:
            # only option flas
            if args[-1] == "-o" or args[-1] == "--output_dir":
                if line[-1] != " ":
                    # insert spaca at the end of option flag
                    comp_args = [args[-1] + " "]
                else:
                    # scan current dir
                    comp_args = [f.name + ("/" if f.is_dir() else "")\
                                for f in os.scandir()]
            elif args[-2] == "-o" or args[-2] == "--output_dir":
                # complement splash
                if text[-2:] == "..":
                    text += "/"
                pos = text.rfind("/")
                if pos != -1:
                    # extract upper directories
                    dir_name = text[:pos+1]
                    remains = text[pos+1:]
                    # scan the upper directories
                    files = os.scandir(dir_name)
                    comp_args = [dir_name + f.name + ("/" if f.is_dir() else "")\
                                for f in files if f.name.startswith(remains)]
                else:
                    # scan current dir
                    files = os.scandir()
                    comp_args = [f.name + ("/" if f.is_dir() else "")\
                                for f in files if f.name.startswith(text)]

        return comp_args

    def help_save(self):
        self.parse_save(["--help"])

    def do_report_hypervolume(self, line):
        if self.__hv_enable:
            if len(self.header["eval_names"]) > 1:
                parsed_args = self.parse_report_hypervolume(line.split(" "))
                if parsed_args is None:
                    return
                # get ref point
                if parsed_args.ref_point is None:
                    # use auto decided ref point
                    hv = self.hypervolume([fit for sublist in self.data["fitness_log"] for fit in sublist])
                    ref_point = hv.refpoint(offset=0.1)
                    print("ref point: ", ref_point, "is used")
                else:
                    ref_point = parsed_args.ref_point
                    if len(ref_point) != len(self.header["eval_names"]):
                        print("Too few or too much values for ref point:", ref_point)
                        return

                # calculate hypervolume
                try:
                    hypervolume_log = [self.hypervolume(fit).compute(ref_point) \
                                if len(fit) > 0 else 0 for fit in self.data["fitness_log"]]
                except ValueError:
                    print("Invalid Ref Point")
                    return

                # get generation size
                gen = range(len(hypervolume_log))

                # check report type
                if parsed_args.type == "png":
                    import matplotlib.pyplot as plt
                    plt.plot(gen, hypervolume_log)
                    plt.xlabel("Generation")
                    plt.ylabel("Hypervolume")
                    if parsed_args.output is None:
                        # show the graph
                        plt.show()
                    else:
                        # save the graph
                        try:
                            plt.savefig(parsed_args.output)
                        except PermissionError:
                            print("Cannot creat file: Permission denied")
                elif parsed_args.type == "csv":
                    try:
                        with open(parsed_args.output, 'w') as f:
                            writer = csv.writer(f, lineterminator='\n')
                            # first col: generation, second: hypervolume
                            writer.writerow(["generation", "hypervolume"])
                            writer.writerows([(g + 1, hv) for g, hv in zip(gen, hypervolume_log)])
                    except PermissionError:
                        print("Cannot creat file: Permission denied")
            else:
                print("This is uni-objective optimization results")
                print("Hypervolume cannot calculated")
        else:
            print("Hypervolume calculator is not available")

    def help_report_hypervolume(self):
        self.parse_report_hypervolume(["--help"])

    def parse_report_hypervolume(self, args):
        usage = "report_hypervolume [options...]\nIt shows hypervolume transition during optimization"
        parser = ArgumentParser(prog = "report_hypervolume", usage=usage)
        parser.add_argument("-t", "--type", type=str, choices=["png", "csv"], default="png",\
                            help="specify report type")
        parser.add_argument("-o", "--output", type=str, help="specify output file name")
        parser.add_argument("--ref-point", type=float, nargs="+", \
                            help="specify reference point for hypervolume calculation")

        try:
            parsed_args = parser.parse_args(args=[argv for argv in args if argv != ""])
        except SystemExit:
             return None

        if parsed_args.type == "csv" and parsed_args.output is None:
            print("For csv report, --output option is necessary")
            return None

        return parsed_args

    def complete_report_hypervolume(self, text, line, begidx, endidx):
        args = line.split(" ")
        args = [argv for argv in args if argv != ""]
        if text == "":
            args.append("")

        OPTIONS = ["-t", "--type", "-o", "--output", "--ref-point"]

        # in case of output option, complete file/directory names
        if len(args) > 0:
            if args[-2] == "-o" or args[-2] == "--output":
                # complement splash
                if text[-2:] == "..":
                    text += "/"
                pos = text.rfind("/")
                if pos != -1:
                    # extract upper directories
                    dir_name = text[:pos+1]
                    remains = text[pos+1:]
                    # scan the upper directories
                    files = os.scandir(dir_name)
                    comp_args = [dir_name + f.name + ("/" if f.is_dir() else "")\
                                for f in files if f.name.startswith(remains)]
                else:
                    # scan current dir
                    files = os.scandir()
                    comp_args = [f.name + ("/" if f.is_dir() else "")\
                                for f in files if f.name.startswith(text)]
            elif args[-2] == "-t" or args[-2] == "--type":
                comp_args = [opt for opt in ["png ", "csv "] if not re.match("^" + text, opt) is None]
            elif not args[-2] in OPTIONS:
                comp_args = [opt + " " for opt in OPTIONS if not re.match("^" + text, opt) is None]

        return comp_args

    @staticmethod
    def __bold_font(s):
        return '\033[1m' + s + '\033[0m'
