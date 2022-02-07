from abc import ABCMeta, abstractmethod
from argparse import ArgumentParser
from os import name, openpty, write
from wsgiref.handlers import IISCGIHandler
from deap import base
from deap import creator
import pickle
import glob
import numpy as np

from GenMapShell import GenMapShell
from ConfDrawer import ConfDrawer
from Individual import Individual
from Application import Application
from PEArrayModel import PEArrayModel
from SimParameters import SimParameters
from MapHeightEval import MapHeightEval
from MapWidthEval import MapWidthEval
from InitiationIntervalEval import InitiationIntervalEval


class StatGen():
    def __init__(self) -> None:
        pass

    def parse_dircname(self):
        parser = ArgumentParser()
        parser.add_argument("DIRC", help="read dump files in this directory")
        args = parser.parse_args()
        return args.DIRC

    def parse_filenames(self):
        dircname = self.parse_dircname()
        filenames = glob.glob(dircname + "/*.dump")
        return filenames


if __name__ == "__main__":
    generator = StatGen()
    filenames = generator.parse_filenames()

    sample_num = len(filenames)
    min_heights = np.zeros(sample_num)
    min_IIs = np.zeros(sample_num)
    min_widths = np.zeros(sample_num)

    for sample_index in range(len(filenames)):
        with open(filenames[sample_index], "rb") as f:
            header = pickle.load(f)
            creator.create("Fitness", base.Fitness,
                           weights=header["fitness_weights"])
            creator.create("Individual", Individual, fitness=creator.Fitness)
            data = pickle.load(f)

            if len(data['hof']) == 0:
                min_heights[sample_index] = np.inf
                min_IIs[sample_index] = np.inf
                min_widths[sample_index] = np.inf
            else:
                indivisuals = data['hof']
                heights = np.zeros(len(indivisuals))
                IIs = np.zeros(len(indivisuals))
                widths = np.zeros(len(indivisuals))

                for ind_index in range(len(indivisuals)):
                    heights[ind_index] = MapHeightEval.eval(
                        header['arch'], header['app'], header['sim_params'], indivisuals[ind_index])
                    IIs[ind_index] = InitiationIntervalEval.eval(
                        header['arch'], header['app'], header['sim_params'], indivisuals[ind_index])
                    widths[ind_index] = MapWidthEval.eval(
                        header['arch'], header['app'], header['sim_params'], indivisuals[ind_index])

                min_heights[sample_index] = np.min(heights)
                min_IIs[sample_index] = np.min(IIs)
                min_widths[sample_index] = np.min(widths)

    min_height = np.min(min_heights)
    min_II = np.min(min_IIs)
    min_width = np.min(min_widths)

    min_heights = min_heights[min_heights != np.inf]
    min_IIs = min_IIs[min_IIs != np.inf]
    min_widths = min_widths[min_widths != np.inf]

    success_num = len(min_heights)

    mean_min_height = np.mean(min_heights)
    mean_min_II = np.mean(min_IIs)
    mean_min_width = np.mean(min_widths)

    stat_rep = 'sample: ' + str(sample_num) + '\n' + \
        'success: ' + str(success_num) + '\n' + \
        'min_hi: ' + str(min_height) + '\n' + \
        'avg_hi: ' + str(mean_min_height) + '\n' + \
        'hi_list: ' + str(min_heights) + '\n' + \
        'min_II: ' + str(min_II) + '\n' + \
        'avg_II: ' + str(mean_min_II) + '\n' + \
        'II_list: ' + str(min_IIs) + '\n' + \
        'min_wi: ' + str(min_width) + '\n' + \
        'avg_wi: ' + str(mean_min_width) + '\n' + \
        'wi_list: ' + str(min_widths) + '\n'

    with open(generator.parse_dircname() + 'stat_report.txt', 'w') as f:
        f.write(stat_rep)

    np.savetxt(generator.parse_dircname() + 'min_heights.txt', min_heights)
    np.savetxt(generator.parse_dircname() + 'min_IIs.txt', min_IIs)
    np.savetxt(generator.parse_dircname() + 'min_widths.txt', min_widths)

    print(stat_rep)
