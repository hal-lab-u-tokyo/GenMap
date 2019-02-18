from abc import ABCMeta, abstractmethod

class EvalBase(metaclass=ABCMeta):
    @staticmethod
    @abstractmethod
    def eval(CGRA, app, sim_params, individual, **info):
        """Return mapping width.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                app (Application): An application to be optimized
                sim_params (SimParameters): parameters for some simulations
                individual (Individual): An individual to be evaluated

            Returns:
                int: mapping width
        """
        pass

    @staticmethod
    @abstractmethod
    def isMinimize():
        """Returns whether this objective should be minimize.
        """
        pass


    @staticmethod
    @abstractmethod
    def name():
        """Returns the evaluation name
        """
        pass
