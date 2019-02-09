from abc import ABCMeta, abstractmethod

class EvalBase(metaclass=ABCMeta):
    @abstractmethod
    def eval(self, CGRA, individual, **info):
        """Return mapping width.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                individual (Individual): an individual to be evaluated

            Returns:
                int: mapping width
        """
        pass

    @abstractmethod
    def isMinimize(self):
        """Returns whether this objective should be minimize.
        """
        pass
