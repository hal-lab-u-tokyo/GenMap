from PEArrayModel import PEArrayModel
from Individual import Individual
import networkx as nx

class DataPathAnalysis():

    @staticmethod
    def get_data_path(CGRA, individual):
        """Analyzes data path on the PE array.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                individual (Individual): An individual to be evaluated

            Returns:
                list: list of path(networkx)
        """

        # data path analysis
        graph = individual.routed_graph
        used_inports = set(graph.nodes()) & set(CGRA.getInputPorts())
        used_outports = set(graph.nodes()) & set(CGRA.getOutputPorts())
        paths = []
        for i_port in used_inports:
            for o_port in used_outports:
                paths.extend([p[1:-1] for p in nx.all_simple_paths(graph, i_port, o_port)])

        # path separation by activate pipeline register
        if CGRA.getPregNumber() != 0:
            data_path = []
            st_domain = CGRA.getStageDomains(individual.preg)
            for p in paths:
                for stage in st_domain:
                    dp = sorted(set(p) & set(stage), key=p.index)
                    if not dp in data_path:
                        data_path.append(dp)
        else:
            data_path = paths

        return data_path

