from cmd import Cmd
from argparse import ArgumentParser
import prettytable
import copy
import readline

class GenMapShell(Cmd):
    prompt = "GenMap shell> "
    intro = "=== GenMap solution selection utility ==="

    def __init__(self, header, data):
        Cmd.__init__(self)
        self.header = header
        self.data = data
        self.filtered_sols = list(copy.deepcopy(self.data["hof"]))
        new_delims = readline.get_completer_delims()
        for c in "=!<>":
            new_delims = new_delims.replace(c, '')
        readline.set_completer_delims(new_delims)

    def do_EOF(self, arg):
        return True;

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
        usage = "sort [objective] [order]\nIt sorts filtered solutions"
        parser = ArgumentParser(usage=usage)
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
        self.parse_sort(["--help"])

    def parse_filter(self, args):
        usage = "filter [objective] [comp_operator] [value]\nIt sorts filtered solutions"
        parser = ArgumentParser(usage=usage)
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

    def help_reset(self):
        print("usage: reset\nIt resets filtering")

    def do_quit(self, _):
        return True

    def help_quit(self, _):
        print("usage: quit\nExits the shell")

    def do_select(self, arg):
        pass

    def help_select(self):
        pass


