from RouterBase import RouterBase
import networkx as nx

USED_LINK_WEIGHT = 10000
ALU_OUT_WEIGTH = 1000

class AStarRouter(RouterBase):

    @staticmethod
    def set_default_weights(CGRA):
        CGRA.setInitEdgeWeight("weight", 1, "SE")
        CGRA.setInitEdgeWeight("weight", 0, "Const")
        CGRA.setInitEdgeWeight("weight", 0, "IN_PORT")
        CGRA.setInitEdgeWeight("weight", 0, "OUT_PORT")
        CGRA.setInitEdgeWeight("weight", ALU_OUT_WEIGTH, "ALU")
        CGRA.setInitEdgeWeight("free", True)

    @staticmethod
    def comp_routing(CGRA, DFG, mapping, **info):
        PE_array = CGRA.getNetwork()

        # get out degree for each node
        out_deg = {v: DFG.out_degree(v) for v in DFG.nodes() if DFG.out_degree(v) > 0 }
        # sort in ascending order
        out_deg = {k: v for k, v in sorted(out_deg.items(), key=lambda x: x[1])}

        # Astar Routing
        fail_path_count = 0
        for src_node in out_deg.keys():
            # get node element on the PE array
            src_alu = CGRA.getNodeName("ALU", pos = mapping[src_node])

            # remove high cost of alu out
            for suc_element in PE_array.successors(src_alu):
                PE_array.edges[src_alu, suc_element]["weight"] = 1

            # route each path
            shared_edges = set()
            for dst_node in DFG.successors(src_node):
                # get one of destination node name
                dst_alu = CGRA.getNodeName("ALU", pos = mapping[dst_node])

                try:
                    path_len = nx.astar_path_length(PE_array, src_alu, dst_alu, weight = "weight")
                    if path_len > ALU_OUT_WEIGTH:
                        raise nx.exception.NetworkXNoPath
                    else:
                        path = nx.astar_path(PE_array, src_alu, dst_alu, weight = "weight")
                        print(path_len, path)
                        for i in range(len(path) - 1):
                            e = (path[i], path[i + 1])
                            if CGRA.isSE(path[i + 1]):
                                shared_edges.add(e)
                                PE_array.edges[e]["weight"] = 0
                            else:
                                PE_array.edges[e]["weight"] = USED_LINK_WEIGHT
                except nx.exception.NetworkXNoPath:
                    print("Fail:", src_node, "->", dst_node)
                    fail_path_count += 1

                # update SE edges link cost
                for e in shared_edges:
                    PE_array.edges[e]["weight"] = USED_LINK_WEIGHT
        print("fail route", fail_path_count)


    @staticmethod
    def const_routing(CGRA, DFG, **info):
        pass
        print(info)

    @staticmethod
    def input_routing(CGRA, DFG, **info):
        pass
        print(info)

    @staticmethod
    def output_routing(CGRA, DFG, **info):
        pass
        print(info)