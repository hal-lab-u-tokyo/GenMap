#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

import matplotlib.pyplot as plt
import matplotlib.patches as pat
import networkx as nx
import pulp

from SolverSetup import SolverSetup

import math
import sys

# setting up for pulp solver
try:
    solver = SolverSetup("ILP").getSolver()
except SolverSetup.SolverSetupError as e:
    print("Fail to setup ILP solver:", e)
    sys.exit()

# drawing setting
pe_margin = 0.15
se_margin = 0.1
pe_color = "skyblue"
se_size = 0.2
se_color = "lightgreen"
alu_scale = 0.3
alu_color = "lightcoral"
pe_size = 1 - pe_margin * 2
preg_color = "purple"
arrow_setting = dict(facecolor='black', width =0.8 ,headwidth=4.0,headlength=4.0,shrink=0.01)
iport_color = "darkorange"
oport_color = "magenta"

class ConfDrawer():

    def __init__(self, CGRA , individual, origin = "bottom-left"):
        """Constructor of this class

            Args:
                CGRA: (PEArrayModel): A model of the CGRA
                individual (Individual): An individual to be evaluated
                origin (str): position of coordinate origin
                    available values are following:
                        "bottom-left", "top-left", "bottom-right", "top-right"
        """

        self.width, self.height = CGRA.getSize()
        self.used_PE = [ [False for y in range(self.height)] for x in range(self.width)]
        self.PE_resources = [ [ [] for y in range(self.height)] for x in range(self.width)]
        self.node_pos = {}
        self.xlbound = 0
        self.ylbound = 0
        self.xubound = 0
        self.yubound = 0

        # io drawing info
        # dict of dict:
        #  key: name (str), val: dict
        #       key, val is as following:
        #       ("pos", position)
        #       ("adjPE", adjacent PE coord)
        self.used_input = {}
        self.used_output = {}
        # count for each position
        # dict of dict
        # 1st key: IO pos, 2nd key: coord of adj PE
        self.io_count = {pos: {} for pos in ["left", "right", "top", "bottom"]}
        self.io_placed_count =  {pos: {} for pos in ["left", "right", "top", "bottom"]}
        # drawing 
        self.io_size = pe_size # it cloud be updated after anylyzeIO
        self.length = pe_size

        for x in range(self.width):
            for y in range(self.height):
                rsc = CGRA.get_PE_resources((x, y))
                self.PE_resources[x][y].append(rsc["ALU"])
                for SEs in rsc["SE"].values():
                    self.PE_resources[x][y].extend(SEs)
                for v in self.PE_resources[x][y]:
                    self.node_pos[v] = (x, y)


        for v in individual.routed_graph.nodes():
            for x in range(self.width):
                for y in range(self.height):
                    if v in self.PE_resources[x][y]:
                        self.used_PE[x][y] = True
                        break
            if CGRA.isIN_PORT(v):
                self.used_input[v] = {}
            if CGRA.isOUT_PORT(v):
                self.used_output[v] = {}

        # get IO config
        if self.analyzeIO(CGRA):
            horizontal_offset = 1 if len(self.io_count["left"]) > 0 \
                or len(self.io_count["right"]) > 0 else 0
            vertical_offset = 1 if len(self.io_count["top"]) > 0 \
                or  len(self.io_count["bottom"]) > 0 else 0
            used_ip_coords = [v["adjPE"] for v in self.used_input.values()]
            used_op_coords = [v["adjPE"] for v in self.used_output.values()]
        else:
            horizontal_offset = 0
            vertical_offset = 0
            used_ip_coords = []
            used_op_coords = []


        used_PE_coords = [(x, y) for x in range(self.width) for y in range(self.height) if self.used_PE[x][y]]

        actual_width = max([x for (x, y) in \
            sum([used_PE_coords, used_ip_coords, used_op_coords], [])]) + 1
        actual_height = max([y for (x, y) in \
            sum([used_PE_coords, used_ip_coords, used_op_coords], [])]) + 1

        # draw the used PEs
        height_diff = self.height - actual_height
        self.width = actual_width
        self.height = actual_height

        self.xubound = self.width + horizontal_offset
        self.yubound = self.height + vertical_offset

        self.fig = plt.figure(figsize=(self.xubound, self.yubound))
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.ax.set_ybound(self.ylbound, self.yubound)
        self.ax.set_xbound(self.xlbound, self.xubound)

        self.node_to_patch = {}

        # coord,pos re-mapping
        io_remap = {pos: pos for pos in ["left", "right", "top", "bottom"]}
        self.preg_remap = lambda preg_pos: preg_pos
        if origin == "top-left":
            self.coord_remap = lambda pos: (pos[0], self.height - 1 - pos[1])
            io_remap["top"], io_remap["bottom"] = io_remap["bottom"], io_remap["top"]
            self.preg_remap = lambda preg_pos: [v - height_diff for v in  preg_pos[::-1]]
        elif origin == "bottom-right":
            self.coord_remap = lambda pos: (self.width - 1 - pos[0], pos[1])
            io_remap["left"], io_remap["right"] = io_remap["right"], io_remap["left"]
        elif origin == "top-right":
            self.coord_remap = lambda pos: (self.width - 1 - pos[0], \
                                                self.height - 1 - pos[1])
            io_remap["left"], io_remap["right"] = io_remap["right"], io_remap["left"]
            io_remap["top"], io_remap["bottom"] = io_remap["bottom"], io_remap["top"]
            self.preg_remap = lambda preg_pos: [v - height_diff for v in  preg_pos[::-1]]
        else:
            self.coord_remap = lambda pos: pos

        self.io_remap = io_remap

    def analyzeIO(self, CGRA):
        # analyze used io pos
        io_pos = ["left", "right", "top", "bottom"]
        # key: pos (str)
        # val: list of port name (str)
        iports_dict = {k: [] for k in io_pos}
        oports_dict = {k: [] for k in io_pos}

        # get used input port for each pos
        for pos in io_pos:
            iports = CGRA.getInputPortsByPos(pos)
            for ip_name, info in self.used_input.items():
                if ip_name in iports:
                    iports_dict[pos].append(ip_name)
                    info["pos"] = pos

        # get used output port for each pos
        for pos in io_pos:
            oports = CGRA.getOutputPortsByPos(pos)
            for op_name, info in self.used_output.items():
                if op_name in oports:
                    oports_dict[pos].append(op_name)
                    info["pos"] = pos

        if len([v for v in self.used_input.values() if "pos" in v]) != \
            len(self.used_input) or \
            len([v for v in self.used_output.values() if "pos" in v]) != \
            len(self.used_output):
            print("Incorrect or nothing about position info. Skip IO drawing")
            for u in iports_dict[pos]:
                del self.used_input[u]
            for u in oports_dict[pos]:
                del self.used_output[u]
            return False
    
        # estimate adjPE for each pos
        g = CGRA.getNetwork()
        for pos in io_pos:
            try:
                # for input
                ipConnPos = {}
                if len(iports_dict[pos]) > 0:
                    for u in iports_dict[pos]:
                        ipConnPos[u] = self.getAdjPECandidates(pos, \
                                            list(g.successors(u)))

                # for output
                opConnPos = {}
                if len(oports_dict[pos]) > 0:
                    for u in oports_dict[pos]:
                        opConnPos[u] = self.getAdjPECandidates(pos, \
                                            list(g.predecessors(u)))

                if CGRA.isIOShared():
                    connPos = ipConnPos.copy()
                    connPos.update(opConnPos)
                    adjPEPos = self.findAdjPE(pos, connPos)
                else:
                    adjPEPos = self.findAdjPE(pos, ipConnPos)
                    adjPEPos.update(self.findAdjPE(pos, opConnPos))
            except Exception as e:
                print("Failed to determine drawing IO position.  Skip IO drawing")
                for u in iports_dict[pos]:
                    del self.used_input[u]
                for u in oports_dict[pos]:
                    del self.used_output[u]
                return False

            for k, v in adjPEPos.items():
                if k in iports_dict[pos]:
                    self.used_input[k]["adjPE"] = v
                else:
                    self.used_output[k]["adjPE"] = v

        # count IO for each position
        info_list = list(self.used_input.values())
        info_list.extend(self.used_output.values())
        for info in info_list:
            coord = info["adjPE"]
            pos = info["pos"]
            if not coord in self.io_count[pos]:
                self.io_count[pos][coord] = 1
                self.io_placed_count[pos][coord] = 0
            else:
                self.io_count[pos][coord] += 1

        max_io_count = max([count for count_list in self.io_count.values() \
                                for count in count_list.values()])
        self.length = pe_size / float(max_io_count)
        if CGRA.isIOShared() and max_io_count > 1:
            print("Warning: the target CGRA shares IO ports for both input and output but some IO are drawn at the same position")

        used_pos = [info["pos"] for info in info_list]
        if "left" in used_pos:
            self.xlbound -= 1
        if "right" in used_pos:
            self.xubound += 1
        if "bottom" in used_pos:
            self.ylbound -= 1
        if "top" in used_pos:
            self.yubound += 1

        return True


    def findAdjPE(self, pos, _connTable):
        prob = pulp.LpProblem("coord_round", pulp.LpMinimize)
        round_coord = {}

        if pos in ["left", "right"]:
            getCoord = lambda coord: coord[1]
            retCoord = lambda coord, val: (coord[0], val)
        else:
            getCoord = lambda coord: coord[0]
            retCoord = lambda coord, val: (val, coord[1])

        coord_range = set([getCoord(coord) for l in _connTable.values()\
                         for coord in l ])
        # remain conntable
        connTable = {}
        for k in _connTable.keys():
            connTable[k] = {v: False for v in coord_range}
            for v in _connTable[k]:
                connTable[k][getCoord(v)] = True

        x = pulp.LpVariable.dicts("coord", (connTable.keys(), coord_range), \
                                     0, 1,  cat = "Binary")

        # objective
        prob += pulp.lpSum([ sum([abs(w - v) for w in coord_range \
                                    if connTable[k][w]]) * x[k][v] \
                            for k in connTable.keys() \
                            for v in coord_range])
        # constraints
        for k in connTable.keys():
            prob += pulp.lpSum([x[k][v] for v in coord_range]) == 1
        for v in coord_range:
            prob += pulp.lpSum([x[k][v] for k in connTable.keys()]) <= 1
        # dont place
        for k in connTable.keys():
            for v in coord_range:
                if not connTable[k][v]:
                    prob += x[k][v] == 0

        stat = prob.solve(solver)
        result = prob.objective.value()
        if pulp.LpStatus[stat] == "Optimal":
            for k in connTable.keys():
                for v in  coord_range:
                    if x[k][v].value() == 1.0:
                        round_coord[k] = retCoord(_connTable[k][0], v)
            return round_coord
        else:
            raise Exception("Fail to decide IO position")


    def getAdjPECandidates(self, pos, connNodes):

        coord_set = set()

        if pos == "left":
            candidate_coord = [(0, y) for y in range(self.height)]
        elif pos == "right":
            candidate_coord = [(self.width - 1, y) \
                                for y in range(self.height)]
        elif pos == "top":
            candidate_coord = [(x, self.height - 1) \
                                for x in range(self.width)]
        elif pos == "bottom":
            candidate_coord = [(x, 0) for x in range(self.width)]

        if pos in ["left", "right"]:
            forCoordSort = lambda pos: pos[1]
        elif pos in ["top", "bottom"]:
            forCoordSort = lambda pos: pos[0]

        for v in connNodes:
            if self.node_pos[v] in candidate_coord:
                coord_set.add(self.node_pos[v])
        # serach further node
        if len(coord_set) == 0:
            raise Exception("Fail to find adjcent PE for IOs")

        return list(coord_set)


    def draw_PEArray(self, CGRA, individual, app):
        """Draws a PE array where application is mapped

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                individual (Individual): An individual to be evaluated
                app (Application): an application mapped to the PE array

            Returns:
                None
        """
        # add PEs
        for x in range(self.width):
            for y in range(self.height):
                if self.used_PE[x][y]:
                    color = pe_color
                else:
                    color = "white"
                pe = self.__make_PE_patch(self.coord_remap((x, y)), color)
                self.ax.add_patch(pe)

        # add ALUs & SEs
        routing_alus = []
        for v in individual.routed_graph.nodes():
            for x in range(self.width):
                for y in range(self.height):
                    if v in self.PE_resources[x][y]:
                        if CGRA.isALU(v):
                            alu = self.__make_ALU_patch(self.coord_remap((x, y)))
                            self.ax.add_patch(alu)
                            self.node_to_patch[v] = alu
                            if "route" in individual.routed_graph.nodes[v].keys():
                                if individual.routed_graph.nodes[v]["route"]:
                                    # routing alu
                                    routing_alus.append((x, y))
                        else:
                            for SE_id, SEs in CGRA.get_PE_resources((x, y))["SE"].items():
                                if v in SEs:
                                    se = self.__make_SE_patch(self.coord_remap((x, y)), SE_id)
                                    self.ax.add_patch(se)
                                    self.node_to_patch[v] = se

        # add op labels
        dfg = app.getCompSubGraph()
        for op_label, (org_x, org_y) in individual.mapping.items():
            if op_label in dfg.nodes():
                opcode = dfg.nodes[op_label]["opcode"]
            else:
                opcode = "RPE"
            (x, y) = self.coord_remap((org_x, org_y))
            self.ax.annotate(opcode, xy=(x + 1 - pe_margin * 3, y + 1 - pe_margin * 2),\
                                size=12)

        # add routing node
        for (org_x, org_y) in routing_alus:
            opcode = CGRA.getRoutingOpcode(\
                CGRA.getNodeName("ALU", pos=(org_x, org_y)))
            (x, y) = self.coord_remap((org_x, org_y))
            self.ax.annotate(opcode, xy=(x + 1 - pe_margin * 3, \
                            y + 1 - pe_margin * 2), size=12)

        # add Input port
        for iport in self.used_input.keys():
            try:
                ip = self.__make_IOPort(iport, True)
                self.ax.add_patch(ip)
                self.node_to_patch[iport] = ip
            except KeyError:
                pass
        # add Output port
        for oport in self.used_output.keys():
            try:
                op = self.__make_IOPort(oport, False)
                self.ax.add_patch(op)
                self.node_to_patch[oport] = op
            except KeyError:
                pass
        # draw routing
        for u, v in individual.routed_graph.edges():
            if u in self.node_to_patch.keys() and \
                v in self.node_to_patch.keys():
                self.ax.annotate("", xy=self.__get_center(self.node_to_patch[v]),\
                            xytext=self.__get_center(self.node_to_patch[u]),\
                             arrowprops=arrow_setting)


        preg_positions = self.preg_remap(CGRA.getPregPositions())
        for i in range(CGRA.getPregNumber()):
            if individual.preg[i]:
                self.ax.add_patch(self.__make_preg(preg_positions[i]))



    @staticmethod
    def __make_PE_patch(coord, color):
        """Makes a square for PE

            Args:
                coord (tuple): coordinate of the PE
                color (str): color of the PE

            Returns:
                patch of matplotlib: a square
        """
        x, y = coord
        return pat.Rectangle(xy = (x + pe_margin, y + pe_margin), \
                            width = pe_size, height = pe_size, \
                            angle = 0, facecolor = color, edgecolor="black")
    @staticmethod
    def __make_ALU_patch(coord):
        """Makes a patch for ALU

            Args:
                coord (tuple): coordinate of the PE

            Returns:
                patch of matplotlib: an ALU
        """
        pos = (coord[0] + 0.5, coord[1] + 0.4)
        x = [0.0, 0.4, 0.5, 0.6, 1.0, 0.8, 0.2]
        y = [0.0, 0.0, 0.2, 0.0, 0.0, 0.7, 0.7, 0.0]

        x = [v * alu_scale + pos[0] for v in x]
        y = [v * alu_scale + pos[1] for v in y]

        return pat.Polygon(xy=list(zip(x, y)), color=alu_color)

    @staticmethod
    def __make_SE_patch(coord, SE_id):
        """Makes a square for SE

            Args:
                coord (tuple): coordinate of the SE
                SE_id (int): ID of the SE

            Returns:
                patch of matplotlib: a square
        """
        x, y = coord
        pos_x = x + pe_margin + se_margin
        # pos_y = y + pe_margin + pe_size - (se_margin + (se_size + se_margin) * (SE_id + 1))
        pos_y = y + pe_margin + pe_size - (se_size + se_margin) * (SE_id + 1)
        return pat.Rectangle(xy = (pos_x, pos_y), \
                                width = se_size, height = se_size, \
                                angle = 0, color = se_color)

    def __make_preg(self, pos):
        """Makes a line for activated pipeline regs

            Args:
                pos (int): position of the preg

            Returns:
                patch of matplotlib: a rectangle
        """
        return pat.Rectangle(xy = (0,pos - pe_margin / 2), \
                                width = self.width, height = pe_margin, \
                                angle = 0, color = preg_color)

    def __make_IOPort(self, node_name, isInput):
        """Makes a triangle for input/oport port

            Args:
                node_name (str): drawn port name
                isInput (str): if it is input port, set to True

            Returns:
                patch of matplotlib: a triangle
        """
        info = self.used_input[node_name] if isInput else \
                self.used_output[node_name]

        adjPEPos = info["adjPE"]
        draw_adjPEPos = self.coord_remap(adjPEPos)
        pos = info["pos"]
        draw_pos = self.io_remap[pos]
        length = self.length
        margin_to_PE = length / 2.0
        placed_count = self.io_placed_count[pos][adjPEPos]
        io_count = self.io_count[pos][adjPEPos]
        port_ofst = ((pe_size / float(io_count * 2))\
                 * (placed_count * 2 + 1))
        color = iport_color if isInput else oport_color

        # calc offset and rotation angles
        if draw_pos == "left":
            pos_x = draw_adjPEPos[0] - margin_to_PE
            pos_y = draw_adjPEPos[1] + pe_margin + port_ofst
            angle = math.radians(270) if isInput else math.radians(90)
        elif draw_pos == "right":
            pos_x = draw_adjPEPos[0] + margin_to_PE + 1
            pos_y = draw_adjPEPos[1] + pe_margin + port_ofst
            angle = math.radians(90) if isInput else math.radians(270)
        elif draw_pos == "top":
            pos_x = draw_adjPEPos[0] + pe_margin + port_ofst
            pos_y = draw_adjPEPos[1] + margin_to_PE + 1
            angle =  math.radians(180) if isInput else math.radians(0)
        elif draw_pos == "bottom":
            pos_x = draw_adjPEPos[0] + pe_margin + port_ofst
            pos_y = draw_adjPEPos[1] - margin_to_PE
            angle = math.radians(0) if isInput else math.radians(180)

        self.io_placed_count[pos][adjPEPos] += 1

        return pat.RegularPolygon(xy = (pos_x, pos_y), radius = length / 2,\
                                numVertices= 3, fc = color, \
                                ec = "black", orientation=angle)


    @staticmethod
    def __get_center(patch):
        """Calculates center coordinate of patch
        """
        if isinstance(patch, plt.Rectangle):
            width = patch.get_width()
            height = patch.get_width()
            x = patch.get_x()
            y = patch.get_y()
            return (x + width / 2, y + height / 2)
        elif isinstance(patch, pat.RegularPolygon):
            return patch.xy
        else:
            xy = patch.get_xy()
            x_list = [x for x, y in xy]
            y_list = [y for x, y in xy]
            min_x = min(x_list)
            max_x = max(x_list)
            min_y = min(y_list)
            max_y = max(y_list)
            return (min_x + (max_x - min_x) / 2, min_y + (max_y - min_y) / 2)



    def show(self):
        """Shows a drawn figure"""
        plt.axis("off")
        self.fig.show()

    def save(self, filepath):
        """Save a drawn figure"""
        plt.axis("off")
        plt.savefig(filepath)
