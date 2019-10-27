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
    def get_penalty_cost():
        return PENALTY_CONST

    @staticmethod
    def set_default_weights(CGRA):
        CGRA.setInitEdgeAttr("weight", 1, "SE")
        CGRA.setInitEdgeAttr("weight", 0, "Const")
        CGRA.setInitEdgeAttr("weight", 0, "IN_PORT")
        CGRA.setInitEdgeAttr("weight", 0, "OUT_PORT")
        CGRA.setInitEdgeAttr("weight", ALU_OUT_WEIGTH, "ALU")

    @staticmethod
    def comp_routing(CGRA, comp_DFG, mapping, routed_graph, **info):
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

            # get destination alus in ascending order of manhattan distance from the src node
            #       key  : dst alu node name
            #       value: operand attributes of edge between the dest and the src
            dest_alus = {CGRA.getNodeName("ALU", pos = mapping[dst_node]): \
                            comp_DFG.edges[src_node, dst_node]["operand"] \
                            if "operand" in comp_DFG.edges[src_node, dst_node] else None for dst_node in \
                            sorted(list(comp_DFG.successors(src_node)), \
                                key=lambda x: AStarRouter.__manhattan_dist(mapping[x], mapping[src_node])) }

            # route each path
            route_cost += AStarRouter.__single_src_multi_dest_route(CGRA, routed_graph, src_alu, dest_alus)


        return route_cost

    @staticmethod
    def const_routing(CGRA, const_DFG, mapping, routed_graph, **info):
        if len(const_DFG.nodes()) == 0:
            return 0

        const_map = AStarRouter.__resource_mapping(CGRA, CGRA.getConstRegs(), const_DFG, mapping, routed_graph)
        if const_map is None:
            return PENALTY_CONST
        else:
            # save const mapping
            nx.set_node_attributes(routed_graph, {c_reg: edges[0][0] \
                                    for c_reg, edges in const_map.items() if len(edges) > 0},\
                                     "value")

        route_cost = 0
        for c_reg, edges in const_map.items():
            dst_alus = {CGRA.getNodeName("ALU", pos=mapping[dst_node]):\
                        const_DFG.edges[(c, dst_node)]["operand"] \
                        if "operand" in const_DFG.edges[(c, dst_node)] else None \
                        for c, dst_node in edges}
            route_cost += AStarRouter.__single_src_multi_dest_route(CGRA, routed_graph, c_reg, dst_alus)

        return route_cost


    @staticmethod
    def input_routing(CGRA, in_DFG, mapping, routed_graph, **info):
        input_map = AStarRouter.__resource_mapping(CGRA, CGRA.getInputPorts(), in_DFG, mapping, routed_graph)
        if input_map is None:
            return PENALTY_CONST
        else:
            # save input mapping
            nx.set_node_attributes(routed_graph, {i_port: edges[0][0] \
                                    for i_port, edges in input_map.items() if len(edges) > 0},\
                                     "map")

        route_cost = 0
        for i_port, edges in input_map.items():
            dst_alus = {CGRA.getNodeName("ALU", pos=mapping[dst_node]):\
                        in_DFG.edges[(i, dst_node)]["operand"] \
                        if "operand" in in_DFG.edges[(i, dst_node)] else None \
                        for i, dst_node in edges}
            route_cost += AStarRouter.__single_src_multi_dest_route(CGRA, routed_graph, i_port, dst_alus)

        return route_cost

    @staticmethod
    def output_routing(CGRA, out_DFG, mapping, routed_graph, preg_conf = None, **info):

        route_cost = 0

        # get output edges
        output_edges = out_DFG.edges()

        # get output node name
        out_port_nodes = CGRA.getOutputPorts()

        # # get alu nodes connected to output port
        alu_list = []
        for v, o in output_edges:
            alu_list.append(CGRA.getNodeName("ALU", pos=mapping[v]))

        # check pipeline structure
        path_extend_nodes = []
        free_last_stage_SEs = set()
        if CGRA.getPregNumber() != 0:
            stage_domains = CGRA.getStageDomains(preg_conf, remove_return_se = True)
            if len(stage_domains) > 1:
                last_stage_nodes = stage_domains[-1]
                path_extend_nodes = [alu for alu in alu_list if not alu in last_stage_nodes]
                free_last_stage_SEs = set(last_stage_nodes) & set(CGRA.getFreeSEs(routed_graph))

        # greedy output routing
        for v, o in output_edges:
            # get alu name
            alu = CGRA.getNodeName("ALU", pos=mapping[v])
            # remove high cost of alu out
            for suc_element in routed_graph.successors(alu):
                routed_graph.edges[alu, suc_element]["weight"] = 1

            src = alu
            if src in path_extend_nodes:
                # extend data path
                path, cost = AStarRouter.__find_nearest_node(routed_graph, src, free_last_stage_SEs)
                if path is None:
                    return PENALTY_CONST
                route_cost += cost

                # update cost and used flag
                for i in range(len(path) - 1):
                    routed_graph.edges[path[i], path[i + 1]]["weight"] = USED_LINK_WEIGHT
                    routed_graph.edges[path[i], path[i + 1]]["free"] = False
                    routed_graph.nodes[path[i]]["free"] = False
                    # remove other input edges
                    remove_edges = [(p, path[i + 1]) for p in routed_graph.predecessors(path[i + 1]) if p != path[i]]
                    routed_graph.remove_edges_from(remove_edges)
                routed_graph.nodes[path[-1]]["free"] = False

                free_last_stage_SEs -= set(path)
                # print("Extended paht", path)
                # change source node, alu -> se
                src = path[-1]

            # output routing
            path, cost = AStarRouter.__find_nearest_node(routed_graph, src, out_port_nodes)
            if path is None:
                return PENALTY_CONST

            route_cost += cost

            # update cost and used flags
            for i in range(len(path) - 1):
                routed_graph.edges[path[i], path[i + 1]]["weight"] = USED_LINK_WEIGHT
                routed_graph.edges[path[i], path[i + 1]]["free"] = False
                routed_graph.nodes[path[i]]["free"] = False
                # remove other input edges
                remove_edges = [(p, path[i + 1]) for p in routed_graph.predecessors(path[i + 1]) if p != path[i]]
                routed_graph.remove_edges_from(remove_edges)
            routed_graph.nodes[path[-1]]["free"] = False
            free_last_stage_SEs -= set(path)
            # print("out", path)

            out_port_nodes.remove(path[-1])

            routed_graph.nodes[path[-1]]["map"] = o

        return route_cost


    @staticmethod
    def __resource_mapping(CGRA, resources, DFG, mapping, routed_graph):
        """Decides resource mapping for const regs or input ports.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                resources (list-like): mapped node names in the PE array graph
                DFG (networkx DiGraph): A graph to be routed
                mapping (dict): mapping of the DFG
                    keys (str): operation node names of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): PE array graph

            Returns:
                dict: const mapping
                    keys (str): resource name of routed_graph
                    values (list): list of edges which are routed from the resources
                    In case of failure, return None
        """

        # get const edges
        routed_edges = DFG.edges()

        # check validation
        if len(set([r for r, v in routed_edges])) > len(resources):
            # Exceed available const reg number
            return None

        # calculate distance
        dist_from_res = {}
        for r, v in routed_edges:
            dist_from_res[(r, v)] = {}
            for res_node in resources:
                alu = CGRA.getNodeName("ALU", pos=mapping[v])
                try:
                    dist = nx.astar_path_length(routed_graph, res_node, alu)
                except nx.exception.NetworkXNoPath:
                    dist = PENALTY_CONST
                dist_from_res[(r, v)][res_node] = dist + 1

        # make pulp problem
        prob = pulp.LpProblem("Make Resouece Mapping", pulp.LpMinimize)

        # make pulp variables
        # first index: edge, second index const reg node
        isMap = pulp.LpVariable.dicts("MAP", (routed_edges, resources), 0, 1, cat="Binary")

        # define problem
        prob += pulp.lpSum([isMap[e][r] * dist_from_res[e][r] for e in routed_edges for r in resources])

        # constraints
        #   to ensure each edge is mapped to a const reg
        for e in routed_edges:
            prob += pulp.lpSum([isMap[e][r] for r in resources]) == 1
        #   to prevent multiple values from being mapped to the same const reg
        for e1, e2 in itertools.combinations(routed_edges, 2):
            for r in resources:
                if e1[0] == e2[0]: # if same value
                    prob += isMap[e1][r] + isMap[e2][r] <= 2
                else:
                    prob += isMap[e1][r] + isMap[e2][r] <= 1

        # solve this ILP
        stat = prob.solve()
        result = prob.objective.value()

        # check result
        if pulp.LpStatus[stat] == "Optimal" and not result is None:
            if result > PENALTY_CONST:
                return None
            else:
                res_mapping = {r: [e for e in routed_edges if isMap[e][r].value() == 1.0] for r in resources}
                return res_mapping
        else:
            return None

    @staticmethod
    def __manhattan_dist(p1, p2):
        """Return manhattan distance between p1 and p2"""
        return (abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))

    @staticmethod
    def __find_nearest_node(graph, src, dsts):
        """Find the nearset node for src from dsts.

            Args:
                src (str): source node
                dsts (list-like): destination nodes

            Returns:
                    (list, int): path, cost
        """
        min_length = PENALTY_CONST
        nearest_node = None
        # find a nearest node greedy
        for dst in dsts:
            try:
                path_len = nx.astar_path_length(graph, src, dst, weight="weight")
                if path_len < min_length:
                    min_length = path_len
                    nearest_node = dst
            except nx.exception.NetworkXNoPath:
                continue

        if nearest_node is None:
            return None, PENALTY_CONST
        else:
            return nx.astar_path(graph, src, nearest_node, weight="weight"), min_length

    @staticmethod
    def __single_src_multi_dest_route(CGRA, graph, src, dsts):
        """Routes a single source to multiple destinations.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                graph (networkx DiGraph): A graph where the paths are routed
                src (str): source node name of the routed edges
                dests (dict): destination nodes of the routed edges
                                key:   dest node names
                                value: operand attribute of the edge
                                        If the edge don't has this attributes, it is None

            Returns:
                int: routing cost
        """
        # route each path
        shared_edges = set()
        route_cost = 0

        if len(dsts) == 0:
            return 0

        for dst, operand in dsts.items():
            try:
                # get path length by using astar
                path_len = nx.astar_path_length(graph, src, dst, weight = "weight")
                if path_len > ALU_OUT_WEIGTH:
                    raise nx.exception.NetworkXNoPath
                else:
                    route_cost += path_len
                    path = nx.astar_path(graph, src, dst, weight = "weight")
                    # print(path_len, path)
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
                    # add operand attr
                    if not operand is None:
                        graph.edges[(path[-2], path[-1])]["operand"] = operand
            except nx.exception.NetworkXNoPath:
                # there is no path
                # print("Fail:", src, "->", dst)
                route_cost += PENALTY_CONST

        # update SE edges link cost and used flag
        for e in shared_edges:
            graph.edges[e]["weight"] = USED_LINK_WEIGHT
            graph.edges[e]["free"] = False
            graph.nodes[e[1]]["free"] = False

        # update ALU out link cost and used flag
        for v in graph.successors(src):
            graph.edges[src, v]["weight"] = USED_LINK_WEIGHT
        graph.nodes[src]["free"] = False
        for v in dsts:
            graph.nodes[v]["free"] = False


        return route_cost

    @staticmethod
    def clean_graph(graph):
        """Cleaning graph"""
        remove_edges = [e for e in graph.edges() if graph.edges[e]["free"] == True]
        graph.remove_edges_from(remove_edges)
        remove_nodes = [v for v in graph.nodes() if graph.nodes[v]["free"] == True]
        # remove_nodes = [v for v in graph.nodes() if graph.in_degree(v) == 0 and graph.out_degree(v) == 0]
        graph.remove_nodes_from(remove_nodes)
