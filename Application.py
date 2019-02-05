import networkx as nx
import copy

class Application():

    def __init__(self):
        self.__DAG = nx.DiGraph()
        self.__Freq = 0.0 # MHz

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

        # check if it is a DAG
        if nx.is_directed_acyclic_graph(g):
            dag = nx.DiGraph(g)
            # check attributes of nodes
            for u, attr in dag.nodes(data=True):
                if len(attr) == 1:
                    k, v = tuple(attr.items())[0]
                    if not k in ["op", "const", "input", "output"]:
                        print("Unknow attribute " + k)
                        return False
                else:
                    print("There is no or too much attributes for " + v)
                    return False
            # check attributes of edges
            for u1, u2, attr in dag.edges(data=True):
                if len(attr) == 1:
                    k, v = tuple(attr.items())[0]
                    if not k in ["operand"]:
                        print("Unknow attribute " + k)
                        return False
                elif len(attr) > 1:
                    print("There are too much attributes for edge " + (u1, u2))
                    return False
        else:
            print(file + " is not directed acyclic graph (DAG)")
            return False
        self.__DAG = dag
        return True

    def setFrequency(self, f):
        """set operation frequency.

            Args:
                f (float): Frequency

            Return: None
        """
        self.__Freq = float(f)

    def getFrequency(self):
        """get operation frequency/

            Args: None

            Return: float: frequecy
        """
        return self.__Freq


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


# test
if __name__ == "__main__":
    app = Application()
    print(app.read_dot("./gray.dot"))
    g = app.getCompSubGraph()
    # import pylab
    # pos = nx.nx_pydot.graphviz_layout(g)
    # labels = nx.get_node_attributes(g, "op")
    # nx.draw(g, pos)
    # nx.draw_networkx_labels(g, pos, labels)
    # # pylab.show()
    # print(labels)

    g2 = app.getConstSubGraph()
    g3 = app.getInputSubGraph()
    g4 = app.getOutputSubGraph()


