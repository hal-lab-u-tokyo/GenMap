from RouterBase import RouterBase
import networkx as nx
import pulp
import itertools

USED_LINK_WEIGHT = 10000
ALU_OUT_WEIGTH = 1000
PENALTY_CONST = 1000

class AStarRouter(RouterBase):

    class InfeasibleRouting(Exception):
        pass

    @staticmethod
    def set_default_weights(CGRA):
        """Set default weight to network model.

            Args:
                CGRA: A model of the CGRA to be initialized

            Returns: None

        """
        CGRA.setInitEdgeWeight("weight", 1, "SE")
        CGRA.setInitEdgeWeight("weight", 0, "Const")
        CGRA.setInitEdgeWeight("weight", 0, "IN_PORT")
        CGRA.setInitEdgeWeight("weight", 0, "OUT_PORT")
        CGRA.setInitEdgeWeight("weight", ALU_OUT_WEIGTH, "ALU")
        CGRA.setInitEdgeWeight("free", True)

    @staticmethod
    def comp_routing(CGRA, comp_DFG, mapping, routed_graph, **info):
        """Routes a computation DFG on the PE array.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                comp_DFG (networkx DiGraph): A graph to be routed
                mapping (dict): mapping of the DFG
                    keys (str): node names of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): PE array graph

            Returns:
                int: routing cost
        """

        # get out degree for each node
        out_deg = {v: comp_DFG.out_degree(v) for v in comp_DFG.nodes() if comp_DFG.out_degree(v) > 0 }
        # sort in ascending order
        out_deg = {k: v for k, v in sorted(out_deg.items(), key=lambda x: x[1])}

        # Astar Routing
        route_cost = 0
        for src_node in out_deg.keys():
            # get node element on the PE array
            src_alu = CGRA.getNodeName("ALU", pos = mapping[src_node])

            # remove high cost of alu out
            for suc_element in routed_graph.successors(src_alu):
                routed_graph.edges[src_alu, suc_element]["weight"] = 1

            # get destination alus
            dest_alus = [CGRA.getNodeName("ALU", pos = mapping[dst_node]) for dst_node in comp_DFG.successors(src_node)]

            # route each path
            route_cost += AStarRouter.single_src_multi_dest_route(CGRA, routed_graph, src_alu, dest_alus)

        return route_cost

    @staticmethod
    def const_routing(CGRA, const_DFG, mapping, routed_graph, **info):
        """Routes a computation DFG on the PE array.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                const_DFG (networkx DiGraph): A graph to be routed
                mapping (dict): mapping of the DFG
                    keys (str): node names of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): PE array graph

            Returns:
                int: routing cost
        """
        if len(const_DFG.nodes()) == 0:
            return 0

        const_map = AStarRouter.const_mapping(CGRA, const_DFG, mapping, routed_graph)
        if const_map is None:
            raise AStarRouter.InfeasibleRouting

        route_cost = 0
        for c_reg, edges in const_map.items():
            shared_edges = set()
            dst_alus = [CGRA.getNodeName("ALU", pos=mapping[dst_node]) for c, dst_node in edges]
            route_cost += AStarRouter.single_src_multi_dest_route(CGRA, routed_graph, c_reg, dst_alus)

        return route_cost


    @staticmethod
    def input_routing(CGRA, in_DFG, mapping, routed_graph, **info):
        input_map = AStarRouter.input_mapping(CGRA, in_DFG, mapping, routed_graph)
        print(input_map)

    @staticmethod
    def output_routing(CGRA, out_DFG, mapping, routed_graph, **info):
        pass

    @staticmethod
    def const_mapping(CGRA, const_DFG, mapping, routed_graph):
        """Make const reg mapping.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                const_DFG (networkx DiGraph): A graph to be routed
                mapping (dict): mapping of the DFG
                    keys (str): node names of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): PE array graph

            Returns:
                dict: const mapping
                    keys (str): const reg name of routed_graph
                    values (list): list of edges which are routed from the const reg
                    In case of failure, return None
        """

        # get const edges
        const_edges = const_DFG.edges()
        # get const regs
        const_regs = CGRA.getConstRegs()

        # check validation
        if len(set([c for c, v in const_edges])) > len(const_regs):
            # Exceed available const reg number
            return None

        # calculate distance
        dist_from_const_reg = {}
        for c, v in const_edges:
            dist_from_const_reg[(c, v)] = {}
            for c_reg in const_regs:
                alu = CGRA.getNodeName("ALU", pos=mapping[v])
                try:
                    dist = nx.astar_path_length(routed_graph, c_reg, alu)
                except nx.exception.NetworkXNoPath:
                    dist = PENALTY_CONST
                dist_from_const_reg[(c, v)][c_reg] = dist

        # make pulp problem
        prob = pulp.LpProblem("Make Const Mapping", pulp.LpMinimize)

        # make pulp variables
        # first index: edge, second index const reg node
        isMap = pulp.LpVariable.dicts("MAP", (const_edges, const_regs), 0, 1, cat="Binary")

        # define problem
        prob += pulp.lpSum([isMap[e][c] * dist_from_const_reg[e][c] for e in const_edges for c in const_regs])

        # constraints
        #   to ensure each edge is mapped to a const reg
        for e in const_edges:
            prob += pulp.lpSum([isMap[e][c] for c in const_regs]) == 1
        #   to prevent multiple values from being mapped to the same const reg
        for e1, e2 in itertools.combinations(const_edges, 2):
            for c in const_regs:
                if e1[0] == e2[0]: # if same value
                    prob += isMap[e1][c] + isMap[e2][c] <= 2
                else:
                    prob += isMap[e1][c] + isMap[e2][c] <= 1

        # solve this ILP
        stat = prob.solve()
        result = prob.objective.value()

        # check result
        if pulp.LpStatus[stat] == "Optimal" and not result is None:
            if result > PENALTY_CONST:
                return None
            else:
                const_mapping = {c: [e for e in const_edges if isMap[e][c].value() == 1.0] for c in const_regs}
                return const_mapping
        else:
            return None


    @staticmethod
    def single_src_multi_dest_route(CGRA, graph, src, dsts):
        """Routes a single source to multiple destinations.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                graph (networkx DiGraph): A graph where the paths are routed
                src (str): source node name on the inputed graph
                dests (list-like): destination nodes on the inputed graph

            Returns:
                int: routing cost
        """
        # route each path
        shared_edges = set()
        route_cost = 0
        for dst in dsts:
            try:
                # get path length by using astar
                path_len = nx.astar_path_length(graph, src, dst, weight = "weight")
                if path_len > ALU_OUT_WEIGTH:
                    raise nx.exception.NetworkXNoPath
                else:
                    route_cost += path_len
                    path = nx.astar_path(graph, src, dst, weight = "weight")
                    print(path_len, path)
                    # set used flag to the links
                    for i in range(len(path) - 1):
                        e = (path[i], path[i + 1])
                        if CGRA.isSE(path[i + 1]):
                            # if the link is provided by SE, set cost 0
                            # for path sharing
                            shared_edges.add(e)
                            graph.edges[e]["weight"] = 0
                            # remove other input edges
                            remove_edges = [(p, path[i + 1]) for p in graph.predecessors(path[i + 1]) if p != path[i]]
                            graph.remove_edges_from(remove_edges)
                        else:
                            # other than SE's
                            graph.edges[e]["weight"] = USED_LINK_WEIGHT
                            graph.edges[e]["free"] = False

            except nx.exception.NetworkXNoPath:
                # there is no path
                print("Fail:", src, "->", dst)
                route_cost += PENALTY_CONST

        # update SE edges link cost
        for e in shared_edges:
            graph.edges[e]["weight"] = USED_LINK_WEIGHT
            graph.edges[e]["free"] = False

        return route_cost

