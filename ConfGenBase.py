from Individual import Individual
from GenMapShell import GenMapShell
from ConfDrawer import ConfDrawer

from abc import ABCMeta, abstractmethod
from argparse import ArgumentParser
from deap import base
from deap import creator
import pickle
import os


class ConfGenBase(metaclass=ABCMeta):

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
        pass

if __name__ == '__main__':
    generator = ConfGenBase()
    generator.main()