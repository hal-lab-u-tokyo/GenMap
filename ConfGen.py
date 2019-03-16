from Individual import Individual
from GenMapShell import GenMapShell
from ConfDrawer import ConfDrawer

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

    # shell = GenMapShell(header, data)

    # while (1):
    #     try:
    #         shell.cmdloop()
    #         break
    #     except KeyboardInterrupt:
    #         shell.intro = ""
    #         print()
    #         continue


    # print()

    # model = header["arch"]

    #####  debug   #####
    from PEArrayModel import PEArrayModel
    import xml.etree.ElementTree as ET
    tree = ET.ElementTree(file="./CMA_conf.xml")
    pearray = tree.getroot()
    if pearray.tag == "PEArray":
        model = PEArrayModel(pearray)

    ##### debug end #####

    width, height = model.getSize()
    drawer = ConfDrawer(width, height)
    drawer.make_PEArray(model)
