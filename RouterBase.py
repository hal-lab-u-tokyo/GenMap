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
                    keys (str): operation label of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): PE array graph

            Returns:
                int: routing cost
        """
        pass