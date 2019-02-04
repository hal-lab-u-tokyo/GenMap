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
            # get node name
            src_alu = CGRA.getNodeName("ALU", pos = mapping[src_node])
            for dst_node in DFG.successors(src_node):
                dst_alu = CGRA.getNodeName("ALU", pos = mapping[dst_node])

                try:
                    path_len = nx.astar_path_length(PE_array, src_alu, dst_alu, weight = "weight")
                    if path_len > ALU_OUT_WEIGTH * 2:
                        raise nx.exception.NetworkXNoPath
                    else:
                        path = nx.astar_path(PE_array, src_alu, dst_alu, weight = "weight")
                        print(path_len, path)
                        for i in range(len(path) - 1):
                            e = (path[0], path[1])
                            PE_array.edges[e]["weight"] = USED_LINK_WEIGHT
                except nx.exception.NetworkXNoPath:
                    fail_path_count += 1
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