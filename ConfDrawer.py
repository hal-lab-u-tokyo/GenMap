import matplotlib.pyplot as plt
import matplotlib.patches as pat

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


class ConfDrawer():

    def __init__(self, CGRA, individual):
        self.width, self.height = CGRA.getSize()
        self.used_PE = [ [False for y in range(self.height)] for x in range(self.width)]
        self.PE_resources = [ [ [] for y in range(self.height)] for x in range(self.width)]

        for x in range(self.width):
            for y in range(self.height):
                rsc = CGRA.get_PE_resources((x, y))
                self.PE_resources[x][y].append(rsc["ALU"])
                for SEs in rsc["SE"].values():
                    self.PE_resources[x][y].extend(SEs)

        for v in individual.routed_graph.nodes():
            for x in range(self.width):
                for y in range(self.height):
                    if v in self.PE_resources[x][y]:
                        self.used_PE[x][y] = True
                        break


        actual_width = max(x for x in range(self.width) for y in range(self.height) if self.used_PE[x][y]) + 1
        actual_height = max(y for x in range(self.width) for y in range(self.height) if self.used_PE[x][y]) + 1

        self.width = actual_width
        self.height = actual_height
        self.fig = plt.figure(figsize=(self.width, self.height))
        self.ax = self.fig.add_subplot(1, 1, 1)

        self.ax.set_ybound(0, self.height)
        self.ax.set_xbound(0, self.width)

        self.node_to_patch = {}


    def draw_PEArray(self, CGRA, individual):
        # add PEs
        for x in range(self.width):
            for y in range(self.height):
                if self.used_PE[x][y]:
                    color = pe_color
                else:
                    color = "white"
                pe = self.__make_PE_patch((x, y), color)
                self.ax.add_patch(pe)



        for v in individual.routed_graph.nodes():
            for x in range(self.width):
                for y in range(self.height):
                    if v in self.PE_resources[x][y]:
                        if CGRA.isALU(v):
                            alu = self.__make_ALU_patch((x, y))
                            self.ax.add_patch(alu)
                            self.node_to_patch[v] = alu
                        else:
                            for SE_id, SEs in CGRA.get_PE_resources((x, y))["SE"].items():
                                if v in SEs:
                                    se = self.__make_SE_patch((x, y), SE_id)
                                    self.ax.add_patch(se)
                                    self.node_to_patch[v] = se


        for u, v in individual.routed_graph.edges():
            if u in self.node_to_patch.keys() and \
                v in self.node_to_patch.keys():
                self.ax.annotate("", xy=self.__get_center(self.node_to_patch[v]),\
                            xytext=self.__get_center(self.node_to_patch[u]),\
                             arrowprops=arrow_setting)


        preg_positions = CGRA.getPregPositions()
        for i in range(CGRA.getPregNumber()):
            if individual.preg[i]:
                self.ax.add_patch(self.__make_preg(preg_positions[i]))

    @staticmethod
    def __make_PE_patch(coord, color):
        x, y = coord
        return pat.Rectangle(xy = (x + pe_margin, y + pe_margin), \
                            width = pe_size, height = pe_size, \
                            angle = 0, facecolor = color, edgecolor="black")
    @staticmethod
    def __make_ALU_patch(coord):

        pos = (coord[0] + 0.5, coord[1] + 0.4)
        x = [0.0, 0.4, 0.5, 0.6, 1.0, 0.8, 0.2]
        y = [0.0, 0.0, 0.2, 0.0, 0.0, 0.7, 0.7, 0.0]

        x = [v * alu_scale + pos[0] for v in x]
        y = [v * alu_scale + pos[1] for v in y]

        return pat.Polygon(xy=list(zip(x, y)), color=alu_color)

    @staticmethod
    def __make_SE_patch(coord, SE_id):
        x, y = coord
        pos_x = x + pe_margin + se_margin
        pos_y = y + pe_margin + pe_size - (se_margin + se_size * (SE_id + 1))
        return pat.Rectangle(xy = (pos_x, pos_y), \
                                width = se_size, height = se_size, \
                                angle = 0, color = se_color)

    def __make_preg(self, pos):
        return pat.Rectangle(xy = (0, pos - pe_margin / 2), \
                                width = self.width, height = pe_margin, \
                                angle = 0, color = preg_color)

    @staticmethod
    def __get_center(patch):
        if isinstance(patch, plt.Rectangle):
            width = patch.get_width()
            height = patch.get_width()
            x = patch.get_x()
            y = patch.get_y()
            return (x + width / 2, y + height / 2)
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
        plt.axis("off")
        self.fig.show()
