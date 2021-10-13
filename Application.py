#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima


import networkx as nx
import copy
from pathlib import Path

class Application():

    TIME_UNIT = {"ps": 10**(-12), "ns": 10**(-9), "us": 10**(-6), "ms": 10**(-3)}
    FREQ_PREFIX = {"G": 10**9, "M": 10**6, "k": 10**3}

    def __init__(self):
        self.__DAG = nx.DiGraph()
        self.__Freq = 10.0 * 10**6 # MHz
        self.__app_name = ""
        # key: node ID
        # value: opcode
        self.__op_nodes = dict()
        # key: node ID
        # value: const value
        self.__const_nodes = dict()
        self.__input_nodes = set()
        self.__output_nodes = set()
        # key: tuple of edge
        # value: int of operand or None
        self.__operands = dict()


    def read_dot(self, file):
        """set application data flow graph to this

        Args:
            file: file path to application dot

        Return:
            bool: whether the read successes or not

        Data requirement
            Node attributes:
                "type" attribute: type of the node
                    1. "op":    operational node
                    2. "const": constant value
                    3. "input": input data from memory (load)
                    4. "output" output data to memory (store)
                Additional attributes for each type
                    For "op" node
                        "opcode" attribute: string of opcode for ALU
                    For "const" node, either "float" or "int" attribute is needed
                        "float" attribute:  float value of the constant
                        "int" attribute:    int value of the constant

            Edge attributes:
                "operand" attributes (optional): int value to specify the dependent data must be inputted to which MUXs.
        """

        try: # read
            g = nx.nx_pydot.read_dot(file)
        except FileNotFoundError:
            print(file + " is not found")
            return False
        except TypeError:
            print(file + " cannot load as dot file")
            return False

        # get app name
        path = Path(file)
        self.__app_name = path.stem

        # check if it is a DAG
        if nx.is_directed_acyclic_graph(g):
            dag = nx.DiGraph(g)
            # check attributes of nodes
            for u, attr in dag.nodes(data=True):
                try:
                    self.__verifyNodeAttr(u, attr)
                except Exception as E:
                    print(E.args)
                    return False
            # check attributes of edges
            for u1, u2, attr in dag.edges(data=True):
                if "operand" in attr:
                    try:
                        operand_int = int(attr["operand"])
                    except ValueError:
                        print("Operand must be a positive integer but",
                                attr["operand"], "is specified for edge",
                                u1, "->", u2)
                        return False
                    self.__operands[(u1,u2)] = operand_int
                else:
                    self.__operands[(u1,u2)] = None

        else:
            print("App Error: " + file + " is not directed acyclic graph (DAG)")
            return False

        # chech input for each node
        for v in dag:
            if dag.in_degree(v) == 0 and dag.out_degree(v) == 0:
                print("App Error: operation ", v, "does not have input and output")

        # add nodes to DAG
        for u, opcode in self.__op_nodes.items():
            self.__DAG.add_node(u, opcode = opcode)
        for u, val in self.__const_nodes.items():
            self.__DAG.add_node(u, value = val)
        self.__DAG.add_nodes_from(self.__input_nodes | self.__output_nodes)
        # add edges to DAG
        for (u1, u2), operand in self.__operands.items():
            self.__DAG.add_edge(u1, u2, operand = operand)

        return True

    def __verifyNodeAttr(self, node, attr):
        if "type" in attr.keys():
            attr_type = attr["type"]
            # op node
            if attr_type == "op":
                if not "opcode" in attr.keys():
                    raise ValueError("Missing opcode for node: ", node)
                else:
                    self.__op_nodes[node] = attr["opcode"]
            # const node
            elif attr_type == "const":
                if "int" in attr.keys():
                    try:
                        cvalue = int(attr["int"])
                    except ValueError:
                        raise ValueError("Invalid value for const integer: ", \
                                            attr["int"])
                elif "float" in attr.keys():
                    try:
                        cvalue = int(attr["float"])
                    except ValueError:
                        raise ValueError("Invalid value for const float: ", \
                                            attr["float"])
                else:
                    raise ValueError("Missing const value (int or float) for node: ", node)
                self.__const_nodes[node] = cvalue
            elif attr_type == "input":
                self.__input_nodes.add(node)
            elif attr_type == "output":
                self.__output_nodes.add(node)
            else:
                raise ValueError("Unknown node type \"{0}\" for node: {1}".format(attr_type, node))
        else:
            raise ValueError("Missing type attribute for node: ", node)

    def getAppName(self):
        """Returns application name
        """
        return self.__app_name

    def setFrequency(self, f, prefix="M"):
        """set operation frequency.

            Args:
                f (float): Frequency
                prefix (str): prefix of frequency unit
                    "G": GHz, "M": MHz, "k": kHz

            Return: None
        """
        self.__Freq = float(f) * self.FREQ_PREFIX[prefix]

    def getFrequency(self, prefix):
        return self.__Freq / self.FREQ_PREFIX[prefix]

    def getClockPeriod(self, time_unit):
        """set operation frequency.

            Args:
                f (float): Frequency
                time_unit (str): time unit
                    "ps": pico sec, "ns": nano sec, "us": micro sec, "ms": milli sec
            Return: None
        """
        return 1 / self.__Freq / self.TIME_UNIT[time_unit]


    def getCompSubGraph(self):
        """get a sub-graph which is composed of only operation nodes
            It does not contain constants and in/out port

            Args: None

            Return:
                networkx digraph: a sub-graph
        """
        subg = copy.deepcopy(self.__DAG)
        remove_nodes = set(subg.nodes()) - set(self.__op_nodes.keys())
        subg.remove_nodes_from(remove_nodes)

        return subg

    def getConstSubGraph(self):
        """get a sub-graph which is composed of const nodes and
            op nodes connected to const nodes

            Args: None

            Return:
                networkx digraph: a sub-graph
        """
        subg = copy.deepcopy(self.__DAG)
        op_nodes = set(self.__op_nodes.keys())
        const_nodes = set(self.__const_nodes.keys())
        const_successors = set([v for u in const_nodes for v in subg.successors(u) ])

        remove_nodes = set(subg.nodes()) - (const_nodes | (op_nodes & const_successors))
        subg.remove_nodes_from(remove_nodes)

        remove_edges = []
        for (u, v) in subg.edges():
            if u in const_successors and v in const_successors:
                remove_edges.append((u, v))
        subg.remove_edges_from(remove_edges)

        return subg

    def getInputSubGraph(self):
        """get a sub-graph which is composed of input nodes and
            op nodes connected to input nodes

            Args: None

            Return:
                networkx digraph: a sub-graph
        """
        subg = copy.deepcopy(self.__DAG)
        op_nodes = set(self.__op_nodes.keys())
        input_successors = set([v for u in self.__input_nodes for v in subg.successors(u) ])

        remove_nodes = set(subg.nodes()) - (self.__input_nodes | (op_nodes & input_successors))
        subg.remove_nodes_from(remove_nodes)

        remove_edges = []
        for (u, v) in subg.edges():
            if u in input_successors and v in input_successors:
                remove_edges.append((u, v))
        subg.remove_edges_from(remove_edges)
        return subg

    def getOutputSubGraph(self):
        """get a sub-graph which is composed of output nodes and
            op nodes connected to output nodes

            Args: None

            Return:
                networkx digraph: a sub-graph
        """
        subg = copy.deepcopy(self.__DAG)
        op_nodes = set(self.__op_nodes.keys())
        output_predecessors = set([v for u in self.__output_nodes for v in subg.predecessors(u) ])

        remove_nodes = set(subg.nodes()) - (self.__output_nodes | (op_nodes & output_predecessors))
        subg.remove_nodes_from(remove_nodes)

        remove_edges = []
        for (u, v) in subg.edges():
            if u in output_predecessors and v in output_predecessors:
                remove_edges.append((u, v))
        subg.remove_edges_from(remove_edges)

        return subg

    def getDAG(self):
        return copy.deepcopy(self.__DAG)

    def hasConst(self):
        """Returns wheather the application has constant values or not.
        """
        return len(self.__const_nodes) > 0

    def extractSubApp(self, op_node_list, new_iport, new_oport):
        """Extracts sub application

            Args:
                op_node_list (list): operational nodes list to be left for
                                        extracted sub application
                new_iport (dict): specifys input port creation
                                    keys: corredponding edge
                                    values: new iport name
                new_oport (dict): specifys output port creation
                                    keys: corresponding edge
                                    values: new oport name
        """

        # get extracted nodes
        remain_nodes = []
        remain_nodes.extend(op_node_list)
        subg_input = set()
        subg_output = set()
        subg_const = []
        new_operands = {}
        for v in self.__input_nodes:
            if len(set(self.__DAG.successors(v)) & set(op_node_list)) > 0:
                remain_nodes.append(v)
                subg_input.add(v)
        for v in self.__output_nodes:
            if len(set(self.__DAG.predecessors(v)) & set(op_node_list)) > 0:
                remain_nodes.append(v)
                subg_output.add(v)
        for v in self.__const_nodes.keys():
            if len(set(self.__DAG.successors(v)) & set(op_node_list)) > 0:
                remain_nodes.append(v)
                subg_const.append(v)

        # make subgraph
        subg_tmp = self.__DAG.subgraph(remain_nodes)
        remain_operands = {e: self.__DAG.edges[e]["operand"] \
                                for e in subg_tmp.edges()}
        subg = nx.DiGraph()
        subg.add_nodes_from(subg_tmp.nodes(data=True))
        subg.add_edges_from(subg_tmp.edges(data=True))

        # create new inport
        for e, iport in new_iport.items():
            subg.add_node(iport, type="input")
            operand = self.__DAG.edges[e]["operand"]
            subg.add_edge(iport, e[1], operand = operand)
            new_operands[(iport, e[1])] = operand
            subg_input.add(iport)

        # create new oport
        for e, oport in new_oport.items():
            subg.add_node(oport, type="output")
            subg.add_edge(e[0], oport)
            new_operands[(e[0], oport)] = None
            subg_output.add(oport)

        # # remove unused const, iport, oport
        # remove_nodes = []
        # for v in subg.nodes():
        #     if subg.degree(v) == 0:
        #         remove_nodes.append(v)
        # subg.remove_nodes_from(remove_nodes)

        # create new application instance
        ret_app = Application()
        ret_app.__DAG = subg
        ret_app.__Freq = self.__Freq
        ret_app.__app_name = self.__app_name
        ret_app.__op_nodes = {u: self.__op_nodes[u] for u in op_node_list}
        ret_app.__const_nodes = {u: self.__const_nodes[u] for u in subg_const}
        ret_app.__input_nodes = subg_input
        ret_app.__output_nodes = subg_output
        ret_app.__operands = remain_operands
        ret_app.__operands.update(new_operands)

        return ret_app


    def getInputCount(self):
        return len(self.__input_nodes)

    def getOutputCount(self):
        return len(self.__output_nodes)