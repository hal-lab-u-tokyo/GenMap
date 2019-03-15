from PEArrayModel import PEArrayModel
from AStarRouter import AStarRouter
from Application import Application
from SimParameters import SimParameters
from Placer import Placer
from Individual import Individual
from WireLengthEval import WireLengthEval
from MapWidthEval import MapWidthEval
from PowerEval import PowerEval
from NSGA2 import NSGA2

import networkx as nx
import pylab

import pickle
import os
import time

from deap import tools
from deap import base
from deap import algorithms
from deap import creator


APP_DOT = "./gray.dot"

# test
if __name__ == "__main__":
    import xml.etree.ElementTree as ET
    tree = ET.ElementTree(file="./CMA_conf.xml")
    pearray = tree.getroot()
    if pearray.tag == "PEArray":
        model = PEArrayModel(pearray)

    # AStarRouter.set_default_weights(model)
    # g = model.getNetwork()

    app = Application()
    app.setFrequency(30, "M")
    app.read_dot(APP_DOT)

    try:
        tree = ET.ElementTree(file="./simdata.xml")
    except ET.ParseError as e:
        print("Parse Error", e.args)
        exit()

    data = tree.getroot()
    try:
        sim_params = SimParameters(model, data)
    except SimParameters.InvalidParameters as e:
        print("Parameter import failed: ", e.args[0])


    tree = ET.ElementTree(file="./OptimizationParameters.xml")
    nsga2_conf = tree.getroot()
    start = time.time()

    logfile = open("./log.txt", "w")

    if nsga2_conf.tag == "Config":
        optimizer = NSGA2(nsga2_conf, logfile)

    if optimizer.setup(model, app, sim_params, AStarRouter, [WireLengthEval, MapWidthEval, PowerEval],\
                        [{}, {}, {"duplicate_enable": True}]):
        hof, hv = optimizer.runOptimization()

    elapsed_time = time.time() - start

    print("elapsed time:", elapsed_time, "[sec]")

    logfile.close()

