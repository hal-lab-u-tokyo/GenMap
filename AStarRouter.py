#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

from RouterBase import RouterBase
from SolverSetup import SolverSetup

import networkx as nx
import pulp
import itertools
import random
import sys

USED_LINK_WEIGHT = 10000
ALU_OUT_WEIGTH = 1000
PENALTY_CONST = 1000

# setting up for pulp solver
try:
    solver = SolverSetup("ILP").getSolver()
except SolverSetup.SolverSetupError as e:
    print("Fail to setup ILP solver:", e)
    sys.exit()


class AStarRouter(RouterBase):

    class InfeasibleRouting(Exception):
        pass

    @staticmethod
    def get_penalty_cost():
        return PENALTY_CONST

    @staticmethod
    def set_default_weights(CGRA):
        # CGRA.setInitEdgeAttr("weight", 1, "SE")
        # CGRA.setInitEdgeAttr("weight", 0, "Const")
        # CGRA.setInitEdgeAttr("weight", 0, "IN_PORT")
        # CGRA.setInitEdgeAttr("weight", 0, "OUT_PORT")
        CGRA.setInitEdgeAttr("weight", ALU_OUT_WEIGTH, "ALU")

    @staticmethod
    def __init_ALU(CGRA, mapping, routed_graph):
        """Initialize ALU nodes in the PE array graph.

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                mapping (dict): mapping of the DFG
                    keys (str): operation label of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): A graph where the paths are routed

            Details:
                For operation mapped ALUs or unused ALU, which can work as routing node,
                    True of "routable" attribute is added.
                    This is a flag for routing.
                    "in_capacity" attribute is added as int.
                    This is a count of in_edges.
                For the other ALUs,
                    False of "routable" attribute is added not to be used as routing node.
        """
        w, h = CGRA.getSize()
        used_coords = mapping.values()
        for x in range(w):
            for y in range(h):
                alu = CGRA.getNodeName("ALU", pos = (x, y))

                if (x, y) in used_coords:
                    # op mapped ALUs
                    routed_graph.nodes[alu]["routable"] = True
                    routed_graph.nodes[alu]["in_capacity"] = \
                        CGRA.getALUMuxCount((x, y))
                else:
                    if CGRA.isRoutingALU((x, y)):
                        # remove high cost of ALU out
                        for suc_element in routed_graph.successors(alu):
                            routed_graph.edges[alu, suc_element]["weight"] = \
                                CGRA.getLinkWeight((alu, suc_element))
                        # Routing ALU candidates
                        routed_graph.nodes[alu]["routable"] = True
                        routed_graph.nodes[alu]["in_capacity"] = 1
                    else:
                        # not used for both op and routing
                        routed_graph.nodes[alu]["routable"] = False

    @staticmethod
    def __remove_other_edges(graph, target, srcs):
        """remove edges other than the specified edges

            Args:
                graph (networkx DiGraph): A graph where the paths are routed
                target (str): target node (successor)
                src (str): predecessor node of the edge to be remained

        """
        remove_edges = [(p, target) for p in \
                            graph.predecessors(target) \
                            if p not in srcs]
        graph.remove_edges_from(remove_edges)

    @staticmethod
    def __rm_ALU_out_cost(CGRA, graph, alu):
        """remove high cost of ALU outputs which are available for the routing

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                graph (networkx DiGraph): A graph where the paths are routed
                alu (str): a node name of the target ALU

        """
        for suc_element in graph.successors(alu):
            if CGRA.isALU(suc_element) and \
                    not graph.nodes[suc_element]["routable"]:
                continue
            e = (alu, suc_element)
            if graph.edges[e]["free"]:
                graph.edges[e]["weight"] = \
                    CGRA.getLinkWeight(e)

    @staticmethod
    def __disable_free_inedge(graph, target):
        """disable all free incoming edge

            Args:
                graph (networkx DiGraph): A graph where the paths are routed
                target (str): target node (successor)
        """
        for e in graph.in_edges(target):
            if graph.edges[e]["free"]:
                graph.edges[e]["weight"] = USED_LINK_WEIGHT

    @staticmethod
    def __mark_used_node(graph, v):
        """mark the node as used

            Args:
                graph (networkx DiGraph): A graph where the paths are routed
                v (str): the used node

        """
        for e in graph.out_edges(v):
            graph.edges[e]["weight"] = USED_LINK_WEIGHT

    @staticmethod
    def __mark_used_edge(graph, e):
        """mark the edge as used

            Args:
                graph (networkx DiGraph): A graph where the paths are routed
                e (tuple of str): the used edge

        """
        graph.edges[e]["weight"] = USED_LINK_WEIGHT
        graph.edges[e]["free"] = False

    @staticmethod
    def comp_routing(CGRA, comp_DFG, mapping, routed_graph, **info):
        AStarRouter.__init_ALU(CGRA, mapping, routed_graph)

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
            AStarRouter.__rm_ALU_out_cost(CGRA, routed_graph, src_alu)

            # get destination alus in ascending order of manhattan distance from the src node
            #       key  : dst alu node name
            #       value: operand attributes of edge between the dest and the src
            dest_alus = {CGRA.getNodeName("ALU", pos = mapping[dst_node]): \
                            comp_DFG.edges[src_node, dst_node]["operand"] \
                            for dst_node in \
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
            return PENALTY_CONST * len(list(const_DFG.edges()))
        else:
            # save const mapping
            nx.set_node_attributes(routed_graph, {c_reg: edges[0][0] \
                                    for c_reg, edges in const_map.items() if len(edges) > 0},\
                                     "value")

        route_cost = 0
        for c_reg, edges in const_map.items():
            dst_alus = {CGRA.getNodeName("ALU", pos=mapping[dst_node]):\
                        const_DFG.edges[(c, dst_node)]["operand"] \
                        for c, dst_node in edges}
            route_cost += AStarRouter.__single_src_multi_dest_route(CGRA, routed_graph, c_reg, dst_alus)

        return route_cost


    @staticmethod
    def input_routing(CGRA, in_DFG, mapping, routed_graph, **info):
        input_map = AStarRouter.__resource_mapping(CGRA, CGRA.getInputPorts(), in_DFG, mapping, routed_graph)
        if input_map is None:
            return PENALTY_CONST * len(list(in_DFG.edges()))
        else:
            # save input mapping
            nx.set_node_attributes(routed_graph, {i_port: edges[0][0] \
                                    for i_port, edges in input_map.items() if len(edges) > 0},\
                                     "map")

        route_cost = 0
        for i_port, edges in input_map.items():
            dst_alus = {CGRA.getNodeName("ALU", pos=mapping[dst_node]):\
                        in_DFG.edges[(i, dst_node)]["operand"] \
                        for i, dst_node in edges}
            route_cost += AStarRouter.__single_src_multi_dest_route(CGRA, routed_graph, i_port, dst_alus)

        return route_cost

    @staticmethod
    def output_routing(CGRA, out_DFG, mapping, routed_graph, preg_conf = None,  dontuse = [], **info):

        route_cost = 0

        # get output edges
        output_edges = out_DFG.edges()

        # get output node name
        out_port_nodes = [oport for oport in CGRA.getOutputPorts()\
                            if not oport in dontuse]

        # # get alu nodes connected to output port
        alu_list = []
        for v, o in output_edges:
            alu_list.append(CGRA.getNodeName("ALU", pos=mapping[v]))

        remain_edges = len(output_edges)

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
            AStarRouter.__rm_ALU_out_cost(CGRA, routed_graph, alu)

            src = alu
            if src in path_extend_nodes:
                # extend data path
                path, cost = AStarRouter.__find_nearest_node(routed_graph, src, free_last_stage_SEs)
                if path is None:
                    return PENALTY_CONST * remain_edges
                route_cost += cost

                # update cost and used flag
                for i in range(len(path) - 1):
                    AStarRouter.__mark_used_edge(routed_graph,\
                                                (path[i], path[i+1]))
                    routed_graph.nodes[path[i]]["free"] = False
                    # remove other input edges
                    AStarRouter.__remove_other_edges(routed_graph, path[i+1],\
                                                        path[i])
                    if CGRA.isALU(path[i+1]):
                        routed_graph.nodes[path[i+1]]["route"] = True
                        routed_graph.nodes[path[i+1]]["in_capacity"] = 0
                routed_graph.nodes[path[-1]]["free"] = False

                free_last_stage_SEs -= set(path)

                AStarRouter.__mark_used_node(routed_graph, src)

                # change source node, alu -> se
                src = path[-1]

            # output routing
            path, cost = AStarRouter.__find_nearest_node(routed_graph, src, out_port_nodes)
            if path is None:
                return PENALTY_CONST * remain_edges
            route_cost += cost

            # update cost and used flags
            for i in range(len(path) - 1):
                AStarRouter.__mark_used_edge(routed_graph,\
                                                (path[i], path[i+1]))
                routed_graph.nodes[path[i]]["free"] = False
                # remove other input edges
                AStarRouter.__remove_other_edges(routed_graph, path[i+1],\
                                                        path[i])
                if CGRA.isALU(path[i+1]):
                    routed_graph.nodes[path[i+1]]["route"] = True
                    routed_graph.nodes[path[i+1]]["in_capacity"] = 0
            routed_graph.nodes[path[-1]]["free"] = False
            free_last_stage_SEs -= set(path)

            # update ALU out link cost and used flag
            AStarRouter.__mark_used_node(routed_graph, src)

            out_port_nodes.remove(path[-1])

            routed_graph.nodes[path[-1]]["map"] = o

            remain_edges -= 1

        return route_cost

    @staticmethod
    def inout_routing(CGRA, in_DFG, out_DFG, mapping, routed_graph, **info):
        io_port = CGRA.getInoutPorts()
        io_map = AStarRouter.__io_mapping(CGRA, io_port, in_DFG, out_DFG, mapping, routed_graph)
        if io_map is None:
            return PENALTY_CONST * (len(list(in_DFG.edges())) + len(list(out_DFG.edges())))
        else:
            input_map, output_map = io_map
            # save io mapping
            nx.set_node_attributes(routed_graph, input_map, "map")
            nx.set_node_attributes(routed_graph, output_map, "map")

        # input routing
        route_cost = 0
        edges = {inode: [] for inode in input_map.values()}
        for (u, v) in in_DFG.edges():
            edges[u].append((u, v))

        for i_port, inode in input_map.items():
            dst_alus = {CGRA.getNodeName("ALU", pos=mapping[dst_node]):\
                        in_DFG.edges[(i, dst_node)]["operand"] \
                        for i, dst_node in edges[inode]}
            route_cost += AStarRouter.__single_src_multi_dest_route(CGRA, routed_graph, i_port, dst_alus)

        # output routing
        for o_port, onode in output_map.items():
            # get source alu
            src_node = list(out_DFG.predecessors(onode))[0]
            alu = CGRA.getNodeName("ALU", pos=mapping[src_node])
            # update link cost around the alu
            AStarRouter.__rm_ALU_out_cost(CGRA, routed_graph, alu)
            # get shortest path
            try:
                path = nx.astar_path(routed_graph, alu, o_port)
                cost = sum([routed_graph.edges[(path[i], path[i+1])]["weight"]\
                             for i in range(len(path) - 1)])

                if cost > ALU_OUT_WEIGTH:
                    route_cost += PENALTY_CONST
                else:
                    # update cost and used flags
                    for i in range(len(path) - 1):
                        AStarRouter.__mark_used_edge(routed_graph,\
                                                (path[i], path[i+1]))
                        routed_graph.nodes[path[i]]["free"] = False
                        # remove other input edges
                        AStarRouter.__remove_other_edges(routed_graph,\
                                                    path[i+1], path[i])
                        if CGRA.isALU(path[i+1]):
                            routed_graph.nodes[path[i+1]]["route"] = True
                            routed_graph.nodes[path[i+1]]["in_capacity"] = 0
                    routed_graph.nodes[path[-1]]["free"] = False

                    # update ALU out link cost and used flag
                    AStarRouter.__mark_used_node(routed_graph, alu)

            except nx.exception.NetworkXNoPath:
                route_cost += PENALTY_CONST

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
        prob = pulp.LpProblem("Make_Resouece_Mapping", pulp.LpMinimize)

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
        stat = prob.solve(solver)
        result = prob.objective.value()

        # check result
        if pulp.LpStatus[stat] == "Optimal" and not result is None:
            res_mapping = {r: [e for e in routed_edges if round(isMap[e][r].value()) == 1] for r in resources}
            return res_mapping
        else:
            return None


    @staticmethod
    def __io_mapping(CGRA, ioports, in_DFG, out_DFG, mapping, routed_graph):
        """Decides io-mapping under the constraint about sharing input port and output port

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                ioport (list-like): list of ioport nodes name (tuple)
                in_DFG (networkx DiGraph): An input graph to be routed
                out_DFG (networkx DiGraph): An output graph to be routed
                mapping (dict): mapping of the DFG
                    keys (str): operation node names of DFG
                    values (tuple): PE coordinates
                routed_graph (networkx DiGraph): PE array graph

            Returns:
                tuple of dict: (input_mapping, output_mapping)
                    For both dict:
                        keys (str): input/output port name of routed_graph
                        values (list): input/output node name of app graph
                        In case of failure, return None
        """

        iport_list = [x[0] for x in ioports]
        oport_list = [x[1] for x in ioports]

        # get in/out edges
        routed_in_edges = in_DFG.edges()
        routed_out_edges = out_DFG.edges()

        # get input/output values
        inodes = set([i for i, v in routed_in_edges])
        onodes = set([o for v, o in routed_out_edges])

        # check validation
        if (len(inodes) + len(onodes)) > len(ioports):
            # Exceed available io port
            return None

        # calculate distance
        dist_from_res = {}
        for i, v in routed_in_edges:
            dist_from_res[(i, v)] = {}
            for ip in iport_list:
                alu = CGRA.getNodeName("ALU", pos=mapping[v])
                try:
                    dist = nx.astar_path_length(routed_graph, ip, alu)
                except nx.exception.NetworkXNoPath:
                    dist = PENALTY_CONST
                dist_from_res[(i, v)][ip] = dist + 1
        for v, o in routed_out_edges:
            dist_from_res[(v, o)] = {}
            for op in oport_list:
                alu = CGRA.getNodeName("ALU", pos=mapping[v])
                try:
                    path = nx.astar_path(routed_graph, alu, op)
                    dist = sum([routed_graph.edges[(path[i], path[i+1])]["weight"]\
                             for i in range(len(path) - 1)])
                    if routed_graph.edges[(path[0], path[1])]["weight"] == ALU_OUT_WEIGTH:
                        if routed_graph.edges[(path[0], path[1])]["free"]:
                            dist -= ALU_OUT_WEIGTH + 1
                except nx.exception.NetworkXNoPath:
                    dist = PENALTY_CONST
                dist_from_res[(v, o)][op] = dist

        # make pulp problem
        prob = pulp.LpProblem("Make_IO_Mapping", pulp.LpMinimize)

        # make pulp variables
        # first index: input/output node, second input/output port
        isInportMap = pulp.LpVariable.dicts("IPMAP", (inodes, iport_list), 0, 1, cat="Binary")
        isOutportMap = pulp.LpVariable.dicts("OPMAP", (onodes, oport_list), 0, 1, cat="Binary")

        # define problem
        prob += pulp.lpSum([isInportMap[e[0]][ip] * dist_from_res[e][ip] for e in routed_in_edges for ip in iport_list]) + \
             pulp.lpSum([isOutportMap[e[1]][op] * dist_from_res[e][op] for e in routed_out_edges for op in oport_list])

        # constraints
        #   to ensure each edge is mapped to a port
        for inode in inodes:
            prob += pulp.lpSum([isInportMap[inode][ip] for ip in iport_list]) == 1
        for onode in onodes:
            prob += pulp.lpSum([isOutportMap[onode][op] for op in oport_list]) == 1
        # to prevent overuse of inout port
        for i in range(len(ioports)):
            prob += pulp.lpSum([isInportMap[inode][iport_list[i]] for inode in inodes]) + \
                        pulp.lpSum([isOutportMap[onode][oport_list[i]] for onode in onodes]) <= 1

        # solve this ILP
        stat = prob.solve(solver)
        result = prob.objective.value()

        # check result
        if pulp.LpStatus[stat] == "Optimal" and not result is None:
            input_mapping = {}
            for inode in inodes:
                for ip in iport_list:
                    if isInportMap[inode][ip].value() == 1.0:
                        input_mapping[ip] = inode
                        break
            output_mapping = {}
            for onode in onodes:
                for op in oport_list:
                    if isOutportMap[onode][op].value() == 1.0:
                        output_mapping[op] = onode
                        break
            return (input_mapping, output_mapping)
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
        path_dict = {}

        # find a nearest node greedy
        for dst in dsts:
            try:
                path = nx.astar_path(graph, src, dst, weight="weight")
                path_len = sum([graph.edges[(path[i], path[i+1])]["weight"]\
                             for i in range(len(path) - 1)])
                path_dict[dst] = path
                if path_len < min_length:
                    min_length = path_len
                    nearest_node = dst
            except nx.exception.NetworkXNoPath:
                continue

        if nearest_node is None:
            return None, PENALTY_CONST
        else:
            return path_dict[nearest_node], min_length

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
                path = nx.astar_path(graph, src, dst, weight = "weight")
                path_len = sum([graph.edges[(path[i], path[i+1])]["weight"]\
                             for i in range(len(path) - 1)])

                if path_len > ALU_OUT_WEIGTH:
                    raise nx.exception.NetworkXNoPath
                else:
                    route_cost += path_len
                    # set used flag to the links
                    for i in range(len(path) - 1):
                        e = (path[i], path[i + 1])
                        isSE = CGRA.isSE(e[1])
                        isALU = CGRA.isALU(e[1])
                        if isSE or (isALU and e[1] != path[-1]):
                            # if the link is provided by SE, set cost 0
                            # for path sharing
                            shared_edges.add(e)
                            graph.edges[e]["weight"] = 0
                            # remove other input edges
                            AStarRouter.__remove_other_edges(graph, path[i+1],\
                                                                path[i])
                            if isALU:
                                graph.nodes[e[1]]["route"] = True
                                graph.nodes[e[1]]["in_capacity"] = 0
                        else:
                            # other than SE's
                            AStarRouter.__mark_used_edge(graph, e)

                    # add operand attr
                    if not operand is None:
                        graph.edges[(path[-2], path[-1])]["operand"] = operand

                    # check input capacity
                    graph.nodes[dst]["in_capacity"] -= 1
                    if graph.nodes[dst]["in_capacity"] == 0:
                        AStarRouter.__disable_free_inedge(graph, dst)

            except nx.exception.NetworkXNoPath:
                # there is no path
                # print("Fail:", src, "->", dst)
                route_cost += PENALTY_CONST

        # update SE edges link cost and used flag
        for e in shared_edges:
            AStarRouter.__mark_used_edge(graph, e)
            graph.nodes[e[1]]["free"] = False

        # update ALU out link cost and used flag
        AStarRouter.__mark_used_node(graph, src)
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
