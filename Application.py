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

    def read_dot(self, file):
        """set application data flow graph to this

        Args:
            file: file path to application dot

        Return:
            bool: whether the read successes or not
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
                if len(attr) == 1:
                    k, v = tuple(attr.items())[0]
                    if not k in ["op", "const", "input", "output"]:
                        print("App Error: Unknow attribute " + k)
                        return False
                else:
                    print("App Error: There is no or too much attributes for \"{0}\"".format(u))
                    return False
            # check attributes of edges
            for u1, u2, attr in dag.edges(data=True):
                if len(attr) == 1:
                    k, v = tuple(attr.items())[0]
                    if not k in ["operand"]:
                        print("App Error: Unknow attribute \"{0}\" between \"{1}\" and \"{2}\"".format(k, u1, u2))
                        return False
                elif len(attr) > 1:
                    print("App Error: There are too much attributes \"{0}\" and \"{1}\"".format(u1, u2))
                    return False
        else:
            print("App Error: " + file + " is not directed acyclic graph (DAG)")
            return False

        # chech input for each node
        for v in dag:
            if dag.in_degree(v) == 0 and dag.out_degree(v) == 0:
                print("App Error: operation ", v, "does not have input and output")
            elif dag.in_degree(v) > 2:
                print("App Error: There is too much input to operation", v)
        self.__DAG = dag
        return True

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
        remove_nodes = set(subg.nodes()) - set(nx.get_node_attributes(subg, "op").keys())
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
        op_nodes = set(nx.get_node_attributes(subg, "op").keys())
        const_nodes = set(nx.get_node_attributes(subg, "const").keys())
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
        op_nodes = set(nx.get_node_attributes(subg, "op").keys())
        input_nodes = set(nx.get_node_attributes(subg, "input").keys())
        input_successors = set([v for u in input_nodes for v in subg.successors(u) ])

        remove_nodes = set(subg.nodes()) - (input_nodes | (op_nodes & input_successors))
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
        op_nodes = set(nx.get_node_attributes(subg, "op").keys())
        output_nodes = set(nx.get_node_attributes(subg, "output").keys())
        output_predecessors = set([v for u in output_nodes for v in subg.predecessors(u) ])

        remove_nodes = set(subg.nodes()) - (output_nodes | (op_nodes & output_predecessors))
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
        return len(nx.get_node_attributes(self.__DAG, "const").keys()) > 0

    def extractSubApp(self, op_node_list, new_iport, new_oport):
        """Extracts sub application

            Args:
                op_node_list (list): operational nodes list to be left for
                                        extracted sub application
                new_iport (dict): specifys input port creation
                                    keys: source op node name
                                    values: new iport name
                new_oport (dict): specifys output port creation
                                    keys: sink op node name
                                    values: new oport name
        """

        # remove other op nodes
        subg = copy.deepcopy(self.__DAG)
        op_nodes = set(nx.get_node_attributes(subg, "op").keys())
        subg.remove_nodes_from(op_nodes - set(op_node_list))

        # remove unused const, iport, oport
        remove_nodes = []
        for v in subg.nodes():
            if subg.degree(v) == 0:
                remove_nodes.append(v)
        subg.remove_nodes_from(remove_nodes)

        # create new inport
        for src, iport in new_iport.items():
            subg.add_node(iport, input="True")
            subg.add_edge(iport, src)

        # create new oport
        for sink, oport in new_oport.items():
            subg.add_node(oport, output="True")
            subg.add_edge(sink, oport)

        # create new application instance
        ret_app = Application()
        ret_app.__DAG = subg
        ret_app.__Freq = self.__Freq
        ret_app.__app_name = self.__app_name

        return ret_app


