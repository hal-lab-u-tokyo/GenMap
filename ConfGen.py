from Individual import Individual
from GenMapShell import GenMapShell

from cmd import Cmd
from deap import base
from deap import creator
import pickle


if __name__ == '__main__':

    f = open("../out.tmp", "rb")
    header = pickle.load(f)

    creator.create("Fitness", base.Fitness, weights=header["fitness_weights"])
    creator.create("Individual", Individual, fitness=creator.Fitness)

    data = pickle.load(f)

    f.close()

    shell = GenMapShell(header, data)

    while (1):
        try:
            shell.cmdloop()
            break
        except KeyboardInterrupt:
            shell.intro = ""
            print()
            continue


    print()