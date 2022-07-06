#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

from GenMapShell import GenMapShell
from ConfDrawer import ConfDrawer
from Individual import Individual
from Application import Application
from PEArrayModel import PEArrayModel
from SimParameters import SimParameters

from abc import ABCMeta, abstractmethod
from argparse import ArgumentParser
from deap import base
from deap import creator
import pickle
import os


class ConfGenBase(metaclass=ABCMeta):

    def __init__(self):
        self.style_types = {}
        self.style_choices = {}
        self.style_default = {}

    def style_args_parser(self, args):
        """argument parser for style option
            Args:
                args (list): list of arguments

            Returns:
                dict or None: without any error, it returns parsed arguments as dict

            An option with an argument is given as "optionanme=argment"

            To set option name and it default value,
            override style_types (dict), style_choices, and style_default (dict)
                style_types:
                    key: option name
                    value: type of the value
                    If the type is boolean, the option is treated as flag option
                    Otherwise, the option needs one argument.
                    It type of the argument is different from the default value,
                    it occurs error
                style_choise:
                    key: option name
                    value: list of choises
                    If an option name is not contained in this dict,
                    the option allows any values
                style_default:
                    key: option name
                    value: default value

        """
        # init by default setting
        parsed_args = {k:v for k,v in self.style_default.items()}
        # parse
        for v in args:
            temp = v.split("=")
            if (len(temp)) == 1:
                if v in self.style_types.keys():
                    if self.style_types[v] == bool:
                        parsed_args[v] = True
                    else:
                        print("-s: {0} is not flag option".format(v))
                        return None
                else:
                    print("-s: unknown option {0}".format(v))
                    return None
            elif (len(temp) == 2):
                if temp[0] in self.style_types.keys():
                    if type(temp[1]) == self.style_types[temp[0]]:
                        if temp[0] in self.style_choices.keys():
                            if not temp[1] in self.style_choices[temp[0]]:
                                print("-s: arguemnt \"{1}\" of {0} is not allowed.\nSelect from {2}".format(\
                                    temp[0], temp[1], self.style_choices[temp[0]]))
                                return None
                        parsed_args[temp[0]] = temp[1]
                    else:
                        if self.style_types[temp[0]] == bool:
                            print("-s: {0} option is flag option, no need of arguement".format(temp[0]))
                        else:
                            print("-s: argument \"{1}\" of {0} is not {2}".format(temp[0], temp[1], \
                                                            self.style_types[temp[0]]))
                        return None
                else:
                    print("-s: unknown option {0}".format(v))
                    return None
            else:
                print("-s: invalid argument", v)
                return None

        return parsed_args

    def main(self):
        args = self.parser()
        filename = args.result
        if not os.path.exists(filename):
            print(filename, " does not exist")
            return

        with open(filename, "rb") as f:
            # load header
            header = pickle.load(f)

            # prepare for loading result data
            creator.create("Fitness", base.Fitness, weights=header["fitness_weights"])
            creator.create("Individual", Individual, fitness=creator.Fitness)

            # load result
            data = pickle.load(f)

        shell = GenMapShell(header, data, self)

        # start Shell
        while (1):
            try:
                shell.cmdloop()
                break
            except KeyboardInterrupt:
                shell.intro = ""
                print()
                continue

    def parser(self):
        usage = 'Usage: python3 {0} optimization_result'.format(self.__class__.__name__ + ".py")
        argparser = ArgumentParser(usage=usage)
        argparser.add_argument("result", type=str, help="optimization result")
        args = argparser.parse_args()
        return args

    @abstractmethod
    def generate(self, header, data, individual_id, args):
        """Generates configuration data for the target architecture

            Args:
                header (dict)       : header of dumpfile
                data (dict)         : data of dumpfile
                individual_id (int) : selected solution ID to be generated
                args (list)         : options from command line

            Raises:
                TypeError:
                    The dumpfile is incompatible for the target archtecture
        """
        pass

if __name__ == '__main__':
    generator = ConfGenBase()
    generator.main()