#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

from abc import ABCMeta, abstractmethod
import networkx as nx

class RouterBase(metaclass=ABCMeta):
    @staticmethod
    @abstractmethod
    def set_default_weights(CGRA):
        """Set default weight to network model.

            Args:
                CGRA (PEArrayModel) : A model of the CGRA to be initialized

            Returns: None

        """
        pass

    @staticmethod
    @abstractmethod
    def comp_routing(CGRA, comp_DFG, mapping, routed_graph, **info):
        """Routes a computation DFG on the PE array.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                comp_DFG (networkx DiGraph): A graph to be routed
                mapping (dict): mapping of the DFG
                    keys (str): operation label of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): PE array graph

            Returns:
                int: routing cost

            Notes:
                This method will add following attributes to routed_graph's edges
                    1. operand: to fix order of operands for an ALU
                Also, this method will add following attributes to routed_graph's nodes
                    1. route: to specifiy routing ALU
        """
        pass

    @staticmethod
    @abstractmethod
    def const_routing(CGRA, const_DFG, mapping, routed_graph, **info):
        """Routes a computation DFG on the PE array.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                const_DFG (networkx DiGraph): A graph to be routed
                mapping (dict): mapping of the DFG
                    keys (str): operation label of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): PE array graph

            Returns:
                int: routing cost

            Notes:
                This method will add following attributes to routed_graph's edges
                    1. operand: to fix order of operands for an ALU
                Also, this method will add following attributes to routed_graph's nodes
                    1. value: constant value which is assigned to an const reg
                    2. route: to specifiy routing ALU

        """
        pass

    @staticmethod
    @abstractmethod
    def input_routing(CGRA, in_DFG, mapping, routed_graph, **info):
        """Routes a computation DFG on the PE array.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                input_DFG (networkx DiGraph): A graph to be routed
                mapping (dict): mapping of the DFG
                    keys (str): operation label of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): PE array graph

            Returns:
                int: routing cost

            Notes:
                This method will add following attributes to routed_graph's edges
                    1. operand: to fix order of operands for an ALU
                Also, this method will add following attributes to routed_graph's nodes
                    1. map: input data which is mapped to an input port
                    2. route: to specifiy routing ALU
        """
        pass

    @staticmethod
    @abstractmethod
    def output_routing(CGRA, out_DFG, mapping, routed_graph, **info):
        """Routes a computation DFG on the PE array.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                out_DFG (networkx DiGraph): A graph to be routed
                mapping (dict): mapping of the DFG
                    keys (str): node names of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): PE array graph
                Optional:
                    preg_conf: Pipeline configuration if the PE Array is pipelined.
                               If it is not None, pipeline latency is adjusted
                               by extending output data path.

            Returns:
                int: routing cost

            Notes:
                This method will add following attributes to routed_graph's nodes
                    1. map: output data which is mapped to a output port
                    2. route: to specifiy routing ALU
        """
        pass

    @staticmethod
    @abstractmethod
    def inout_routing(CGRA, in_DFG, out_DFG, mapping, routed_graph, **info):
        """Routes a computation DFG on the PE array.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                in_DFG (networkx DiGraph): An input data graph to be routed
                out_DFG (networkx DiGraph): An output data graph to be routed
                mapping (dict): mapping of the DFG
                    keys (str): node names of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): PE array graph

            Returns:
                int: routing cost

            Notes:
                This method will add following attributes to routed_graph's nodes
                    1. map: output data which is mapped to a inout port
                    2. route: to specifiy routing ALU
        """
        pass