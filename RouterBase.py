from abc import ABCMeta, abstractmethod
import networkx as nx

class RouterBase(metaclass=ABCMeta):
    @staticmethod
    @abstractmethod
    def set_default_weights(CGRA):
        pass

    @staticmethod
    @abstractmethod
    def comp_routing(CGRA, comp_DFG, mapping, routed_graph, **info):
        pass

    @staticmethod
    @abstractmethod
    def const_routing(CGRA, const_DFG, mapping, routed_graph, **info):
        pass

    @staticmethod
    @abstractmethod
    def input_routing(CGRA, in_DFG, mapping, routed_graph, **info):
        pass

    @staticmethod
    @abstractmethod
    def output_routing(CGRA, out_DFG, mapping, routed_graph, **info):
        pass