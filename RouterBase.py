from abc import ABCMeta, abstractmethod
import networkx as nx

class RouterBase(metaclass=ABCMeta):
    @staticmethod
    @abstractmethod
    def comp_routing(CGRA, DFG, mapping, **kwargs):
        pass

    @staticmethod
    @abstractmethod
    def const_routing(CGRA, DFG, **kwargs):
        pass

    @staticmethod
    @abstractmethod
    def input_routing(CGRA, DFG, **kwargs):
        pass
    
    @staticmethod
    @abstractmethod
    def output_routing(CGRA, DFG, **kwargs):
        pass
