from abc import ABCMeta, abstractmethod

class EvalBase(metaclass=ABCMeta):
    @abstractmethod
    def eval(self, CGRA, individual, **info):
        pass

    @abstractmethod
    def isMinimize(self):
        pass
