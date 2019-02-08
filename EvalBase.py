from abc import ABCMeta, abstractmethod

class EvalBase(metaclass=ABCMeta):
    @staticmethod
    @abstractmethod
    def eval(CGRA, individual, **info):
        pass