from cmd import Cmd
from argparse import ArgumentParser
import prettytable
import copy
import readline
import os

from ConfDrawer import ConfDrawer



class GenMapShell(Cmd):
    prompt = "GenMap shell> "
    intro = "=== GenMap solution selection utility ==="

    def __init__(self, header, data):
        Cmd.__init__(self)
        self.header = header
        self.data = data
        self.filtered_sols = list(copy.deepcopy(self.data["hof"]))
        new_delims = readline.get_completer_delims()
        for c in "=!<>./-":
            new_delims = new_delims.replace(c, '')
        readline.set_completer_delims(new_delims)
        self.selected_id = -1

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
        usage = "filter {0} {1} {2}\nIt sorts filtered solutions".format(\
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

    def help_quit(self, _):
        print("usage: quit\nExits the shell")

    def do_select(self, line):
        args = line.split(" ")
        if len(args) != 1:
            self.help_select()
        else:
            try:
                sol_id = int(args[0])
            except ValueError:
                print("select: {0} is not integer value".format(args[0]))
                return;
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
            drawer = ConfDrawer(model, ind)
            drawer.draw_PEArray(model, ind)
            drawer.show()

    def help_view(self):
        print("usage: view\nIt shows the selected solution")

    def do_save(self):
        parsed_args = self.parse_save(line.split(" "))

        if not parsed_args is None:
            print(parsed_args)

    def parse_save(self, args):
        usage = "save [options...]\nIt sorts filtered solutions"
        parser = ArgumentParser(prog = "save", usage=usage)
        parser.add_argument("-o", "--output_dir", type=str, \
                            help="specify output directory name (default: app_name)")
        parser.add_argument("-f", "--force", action='store_true', \
                            help="overwrite without prompt")
        parser.add_argument("-p", "--prefex", type=str, \
                            help="specify prefex of output file names (default: app_name)",\
                            defalt=self.header["app"].getAppName())

        try:
            parsed_args = parser.parse_args(args=args)
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
            if args[-1] == "-o" or args[-1] == "--output":
                if line[-1] != " ":
                    # insert spaca at the end of option flag
                    comp_args = [args[-1] + " "]
                else:
                    # scan current dir
                    comp_args = [f.name + ("/" if f.is_dir() else "")\
                                for f in os.scandir()]
            elif args[-2] == "-o" or args[-2] == "--output":
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
        pass

    @staticmethod
    def __bold_font(s):
        return '\033[1m' + s + '\033[0m'
