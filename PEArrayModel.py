#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

import networkx as nx
import copy

ALU_node_exp = "ALU_{pos[0]}_{pos[1]}"
SE_node_exp = "SE_{id}_{name}_{pos[0]}_{pos[1]}"
CONST_node_exp = "CONST_{index}"
IN_PORT_node_exp = "IN_PORT_{index}"
OUT_PORT_node_exp = "OUT_PORT_{index}"

DEFAULT_EDGE_WEIGHT = {"ALU": 1, "SE": 1, "IN_PORT": 0, "OUT_PORT": 0, "Const": 0}

DEFAULT_MUX_NUM = 2

class PEArrayModel():

    class InvalidConfigError(Exception):
        pass

    def __init__(self, conf):
        '''Constructor of this class

        Args:
            conf (XML Element): Specification of the PE array
            It must contain following attributes
                name: architecture name
                width: PE array width
                height: PE array height
                const_reg: the number of constant registers
                input_port: the number of input port
                output_port: the number of output port
                inout_port: the number of inout port
            Please note you can use either a pair of input_port and output port or inout_port.
            And also, it must contain a child elements whose tag name is "PE", "PREG", "IN_PORT" or "OUT_PORT".

            "PE" Element will be composed of
                an "ALU" Element
                "SE" Elements
            And also, it must have its coordinate as a attribute named "coord"
            If body bias control is supported, the domain name of its PE is needed as a attribute named "bbdomain"
            Examples:
                 <PE coord="(0, 0)">...</PE>
                 <PE coord="(0, 0)" bbdomain="0">...</PE>

            "ALU" Element has an option attribute "mux_num" regarding the number of input (default: 2).
            Examples:
                <ALU mux_num="3" > ...

            This elemenet will be composed of
                "operation" Elements
                "input" Elements

            "SE" Element will be composed of
                "output" Elements
            And also, it must have its id as a attribute named "id"
            Example:
                <SE id="0">...</SE>

            "operation" Element has an inner text of the operation name supported by the ALU.
            Also, it must have an attributes named "value" for configration data.
            Example:
                <operation value="1" >ADD</operation>

            "output" Element is a output link of the SE.
            It must have its own name as a attribute named "name"
            Example:
                <output name="OUT_NORTH">...</output>

            "input" Element will be used to specify the connection between two Elements.
            It must have 3 essential attributes and 3 optional attrbutes as follows.
                Essential:
                    name: name of this connection
                    type: a type of source node
                    value: integer value of configuration data
                Optional:
                    coord: coordinate of the source node
                        If type is ALU or SE, it is necessary.
                    id: id of the SE node
                        If type is SE, it is necessay.
                    src_name: a source SE's link name
                         If type is SE, it is necessay.
                    index: index of the node
                        If type is Const or IN_PORT, it is necessay
            Examples:
                <input name="ALU" type="ALU" value="0", coord="(0,0)"/>
                <input name="IN_EAST" type="SE" id="0" value="2" src_name="OUT_WEST" coord="(1, 0)"/>
                <input name="IN_SOUTH" type="IN_PORT" value="1" index="0" />
                <input name="IN_CONST_A" type="Const" value="6" index="0"/>

            "PREG" Elements are pipeline registers.
            It must have a attribute "vpos" as a vetical position.
            If vpos = y, it means the pipeline register is placed between (y - 1)th PE rows and yth PE rows.

            "OUT_PORT" Element will be composed of "input" elements

            "IN_PORT" and "OUT_PORT" can have an optional attiribute named "pos".
            It is used to specify where each port is placed in the PE array.
            This attribute is valid for the following values:
                "bottom", "top", "left", "right"


        Raise:
            If there exist invalid configurations, it will raise
                ValueError or InvalidConfigError
        '''

        # init all member variables
        self.__network = nx.DiGraph()
        self.__width = 0
        self.__height = 0
        self.__arch_name = ""
        self.__const_reg_range = []
        self.__in_port_range = []
        self.__out_port_range = []
        self.__inout_used = True
        self.__link_weight = {}

        # operation list supported by the PEs
        #    1st index: pos_x
        #    2nd index: pos_y
        #    value    : list of opcodes
        self.__operation_list = []

        # maximum number of ALU inputs
        #    1st index: pos_x
        #    2nd index: pos_y
        #    value    : list of opcodes
        self.__mux_count = []

        # resources for each body bias domain
        #    1st key: domain name
        #    2nd key: "ALU" or "SE"
        #    value: list of resource node names
        self.__bb_domains = {}

        # pipeline regs positions (list)
        self.__preg_positions = []

        # SE list
        #    1st key: coord
        #    2nd key: SE ID
        #    value  : set of SE node nodes
        self.__se_lists = {}

        # SEs whose return_only attr is True
        self.__return_only_se = []

        # network configuration data value
        #    1st key: successor node name
        #    2nd key: predecessor node name
        #    value  : configuration value
        self.__config_net_table = {}

        # operation configuration data value
        #    1st index: x_pos
        #    2nd index: y_pos
        #    3rd key: opcode
        #    value   ; configration value
        self.__config_op_table = []

        # output names of SE
        #    key:   SE node name
        #    value: output name defined by config file
        self.__output_names = {}

        # list of PEs, which are available for routing
        #   values are coordinate of the ALUs
        self.__routing_ALU = []

        # opcode for routing
        #   key: node name of ALU
        #   values: opcode
        self.__routing_opcode = {}

        # const attributes
        self.__infini_const = False

        # heterogeneity of ISA
        self.__heteroISA = False

        # ALU list for each op
        #   keys:   opcode name
        #   values: list of ALU coord
        self.__supported_ALU = {}

        # IO placement
        self.__input_pos = {"left": [], "right": [], "top": [], "bottom": []}
        self.__output_pos = {"left": [], "right": [], "top": [], "bottom": []}

        # get architecture name
        name_str = conf.get("name")
        if name_str == None:
            raise self.InvalidConfigError("missing attribute of architecure name: name")
        else:
            if name_str == "":
                raise ValueError("Ivalid attribute of archirecture name: name")
            else:
                self.__arch_name = name_str

        # init PE array width
        width_str = conf.get("width")
        if width_str == None:
            raise self.InvalidConfigError("missing PE array attribute: width")
        elif width_str.isdigit() == False:
            raise ValueError("Invalid PE array attribute: width")
        else:
            self.__width = int(width_str)
            if not self.__width > 0:
                raise ValueError("PE width must be greater than 0")

        # init PE array height
        height_str = conf.get("height")
        if height_str == None:
            raise self.InvalidConfigError("missing PE array attribute: height")
        elif height_str.isdigit() == False:
            raise ValueError("Invalid PE array attribute: height")
        else:
            self.__height = int(height_str)
            if not self.__height > 0:
                raise ValueError("PE height must be greater than 0")

        # init PE array const
        const_str = conf.get("const_reg")
        if const_str == None:
            raise self.InvalidConfigError("missing PE array attribute: const_reg")
        elif const_str.isdigit() == False:
            if const_str == "X" or const_str == "x":
                self.__infini_const = True
            else:
                raise ValueError("Invalid PE array attribute: const_reg")
        else:
            self.__const_reg_range = list(range(int(const_str)))
        for c_reg in self.__const_reg_range:
            self.__network.add_node(CONST_node_exp.format(index=c_reg))

        # init PE array inout port
        inoutport_str = conf.get("inout_port")
        if inoutport_str == None:
            self.__inout_used = False
        elif inoutport_str.isdigit() == False:
            raise ValueError("Invalid PE array attribute: inout_port")
        else:
            inout_size = int(inoutport_str)
            if inout_size <= 0:
                print("Warnning: the size of inout port is less than or equal to zero")
                self.__inout_used = False
            else:
                # virtually create both inpout port and output port
                self.__in_port_range = list(range(inout_size))
                self.__out_port_range = list(range(inout_size))
                for i in self.__in_port_range:
                    self.__network.add_node(IN_PORT_node_exp.format(index=i))


        if not self.__inout_used:
            # init PE array inport
            inport_str = conf.get("input_port")
            if inport_str == None:
                raise self.InvalidConfigError("missing PE array attribute: input_port")
            elif inport_str.isdigit() == False:
                raise ValueError("Invalid PE array attribute: input_port")
            else:
                self.__in_port_range = list(range(int(inport_str)))
            for iport in self.__in_port_range:
                self.__network.add_node(IN_PORT_node_exp.format(index=iport))

            # init PE array outport
            outport_str = conf.get("output_port")
            if outport_str == None:
                raise self.InvalidConfigError("missing PE array attribute: output_port")
            elif outport_str.isdigit() == False:
                raise ValueError("Invalid PE array attribute: output_port")
            else:
                self.__out_port_range = list(range(int(outport_str)))

        # init operation list
        self.__operation_list = [[[] for y in range(self.__height)] for x in range(self.__width)]
        # init conf op table
        self.__config_op_table = [[{} for y in range(self.__height)] for x in range(self.__width)]


        # init mux count with default value
        self.__mux_count = [[DEFAULT_MUX_NUM for y in range(self.__height)] \
                            for x in range(self.__width)]

        # get PREG configs
        pregs = [preg for preg in conf if preg.tag == "PREG"]
        for preg in pregs:
            vpos_str = preg.get("vpos")
            if vpos_str is None:
                raise self.InvalidConfigError("missing PREG vertical position")
            elif vpos_str.isdigit() == False:
                raise ValueError("Invalid PREG vertical position: " + vpos_str)
            else:
                self.__preg_positions.append(int(vpos_str))

        self.__preg_positions.sort()

        # init SE list
        for x in range(self.__width):
            for y in range(self.__height):
                self.__se_lists[(x,y)] = {}

        # get PE configs
        PEs = [pe for pe in conf if pe.tag == "PE"]

        # check config number
        if len(PEs) != self.__width * self.__height:
            raise self.InvalidConfigError("The number of PE configs is {0}" +  \
                "but the specified array size is {1}x{2}".format(len(PEs), self.__width, self.__height))

        # load PE configs & add to network
        connections = {}
        for pe in PEs:
            # check coordinate
            coord_str = pe.get("coord")
            if coord_str is None:
                raise self.InvalidConfigError("missing PE coordinate")
            elif coord_str:
                (x, y) = self.__coord_str2tuple(coord_str)

            # check body bias domain
            if not pe.get("bbdomain") is None:
                if not pe.get("bbdomain") in self.__bb_domains.keys():
                    self.__bb_domains[pe.get("bbdomain")] = {"ALU": [], "SE": []}

            # ALU
            if len(list(pe.iter("ALU"))) != 1:
                raise self.InvalidConfigError("missing an ALU for PE({0}) or it has more than one PEs".format((x, y)))
            ALU = list(pe.iter("ALU"))[0]
            # get mux num option
            mux_num_str = ALU.get("mux_num")
            if mux_num_str is not None:
                try:
                    mux_num = int(mux_num_str)
                except ValueError:
                    raise self.InvalidConfigError( \
                        "Invalid mux count for ALU({0},{1}): {2}".format(\
                            x, y, mux_num_str))
                if mux_num <= 0:
                    raise self.InvalidConfigError("Mux count for ALU({0},{1}) must be positive integer but {2} was specified".format(\
                            x, y, mux_num))
                self.__mux_count[x][y] = mux_num
            self.__network.add_node(ALU_node_exp.format(pos=(x, y)))
            if not pe.get("bbdomain") is None:
                self.__bb_domains[pe.get("bbdomain")]["ALU"].append(ALU_node_exp.format(pos=(x, y)))
            for op in ALU.iter("operation"):
                if str(op.text) != "":
                    self.__operation_list[x][y].append(str(op.text))
                else:
                    raise self.InvalidConfigError("Empty opcode for ALU at " + str((x, y)))
                conf_val_str = op.get("value")
                if not conf_val_str is None:
                    try:
                        conf_val = int(conf_val_str)
                    except ValueError:
                        raise ValueError("Invalid configration value for opcode: " \
                                            + str(op.text))
                    self.__config_op_table[x][y][op.text] = conf_val
                else:
                    raise self.InvalidConfigError("missing configuration value for opcode: "\
                                                    + str(op.text))
                # check routing ability
                route_op = op.get("route")
                if not route_op is None:
                    route_op = str(route_op)
                    if route_op not in ["true", "false"]:
                        raise self.InvalidConfigError("unknown value for route attribute of opcode: " + route_op + \
                            "Either \"true\" or \"false\" must be specified")
                    elif route_op == "true":
                        self.__routing_ALU.append((x, y))
                        self.__routing_opcode[ALU_node_exp.format(pos=(x, y))] = op.text

            connections[ALU_node_exp.format(pos=(x, y))] = ALU.iter("input")

            # SE
            for se in pe.iter("SE"):
                # check id of the SE
                if se.get("id") is None:
                    raise self.InvalidConfigError("missing SE id")
                else:
                    try:
                        se_id = int(se.get("id"))
                    except ValueError:
                        raise ValueError("Invalid SE id: " + se.get("id"))
                for output in se.iter("output"):
                    if output.get("name") is None:
                        raise self.InvalidConfigError("missing output name of SE at ({0}, {1})".format((x, y)))
                    se_node_name = SE_node_exp.format(pos=(x, y), name=output.get("name"), id=se_id)
                    self.__network.add_node(se_node_name)
                    if not pe.get("bbdomain") is None:
                        self.__bb_domains[pe.get("bbdomain")]["SE"].append(\
                                se_node_name)
                    connections[se_node_name] = output.iter("input")
                    if not se_id in self.__se_lists[(x, y)].keys():
                        self.__se_lists[(x, y)][se_id] = set()
                    self.__se_lists[(x, y)][se_id].add(se_node_name)
                    self.__output_names[se_node_name] = output.get("name")
                    if output.get("return_only") == "True":
                        self.__return_only_se.append(se_node_name)

        # get output connections
        for ele in conf:
            if ele.tag == "OUT_PORT":
                if ele.get("index") is None:
                    raise self.InvalidConfigError("missing OUT_PORT index")
                else:
                    try:
                        oport_index = int(ele.get("index"))
                    except ValueError:
                        raise ValueError("Invalid OUT_PORT index: " + ele.get("index"))
                    if not oport_index in self.__out_port_range:
                        raise self.InvalidConfigError("OUT_PORT index {0} is out of range".format(oport_index))
                connections[OUT_PORT_node_exp.format(index=oport_index)] = ele.iter("input")
                # check position setting
                if not ele.get("pos") is None:
                    pos = ele.get("pos")
                    if not pos in self.__output_pos.keys():
                        raise self.InvalidConfigError("Unknown OUT_PORT {0} position: {1}".format(oport_index, pos))
                    else:
                        self.__output_pos[pos].append(oport_index)

        # make connections
        for dst, srcs in connections.items():
            self.__make_connection(dst, srcs)


        # get input position setting
        for ele in conf:
            if ele.tag == "IN_PORT":
                if ele.get("index") is None:
                    raise self.InvalidConfigError("missing IN_PORT index")
                else:
                    try:
                        iport_index = int(ele.get("index"))
                    except ValueError:
                        raise ValueError("Invalid IN_PORT index: " + ele.get("index"))
                    if not iport_index in self.__in_port_range:
                        raise self.InvalidConfigError("IN_PORT index {0} is out of range".format(iport_index))
                if not ele.get("pos") is None:
                    pos = ele.get("pos")
                    if not pos in self.__input_pos.keys():
                        raise self.InvalidConfigError("Unknown IN_PORT {0} position: {1}".format(iport_index, pos))
                    else:
                        self.__input_pos[pos].append(iport_index)

        # sort of io position list in asc order
        for v in self.__input_pos.values():
            v.sort()
        for v in self.__output_pos.values():
            v.sort()

        # check io position setting
        lack = set(self.__in_port_range) - \
            set([inner for outer in self.__input_pos.values() \
                 for inner in outer])
        if len(self.__in_port_range) > len(lack) > 0:
            print("Warning: positions for some IN_PORTs ({0}) are not specified".format(lack))
        lack = set(self.__out_port_range) - \
            set([inner for outer in self.__output_pos.values() \
                for inner in outer])
        if len(self.__out_port_range) > len(lack) > 0:
            print("Warning: positions for some OUT_PORTs ({0}) are not specified".format(lack))


        # set node attributes
        nx.set_node_attributes(self.__network, True, "free")
        # set edge attributes
        self.setInitEdgeAttr("free", True)

        # analyze ISA
        base = set(self.__operation_list[0][0])
        for x in range(self.__width):
            for y in range(self.__height):
                if base != set(self.__operation_list[x][y]):
                    self.__heteroISA = True
                    break
        all_ops = set([op for cols in self.__operation_list\
                        for pe in cols for op in pe])
        for op in all_ops:
            self.__supported_ALU[op] = \
                [(x, y) for x in range(self.__width) \
                    for y in range(self.__height) \
                        if op in self.__operation_list[x][y]]

    def __reg_config_net_table(self, dst, src, value):
        """Regists configuration data table for PE array network.

            Args:
                dst (str): destionation node name
                src (str): source node name
                value (int): configration value when routing from src to dst

            Returns:
                None
        """
        if not dst in self.__config_net_table.keys():
            self.__config_net_table[dst] = {}
        self.__config_net_table[dst][src] = value

    def __make_connection(self, dst, srcs):
        """Makes connction from multiple source nodes to a destionation node

            Args:
                dst (src): destionation node name
                srcs (list of XML Element): source node

            Returns:
                None
        """
        for src in srcs:
            # parse input info
            attr = self.__parse_input(dst, src)

            if attr["type"] == "ALU": # add edge from ALU
                if not attr["coord"] is None:
                    alu = ALU_node_exp.format(pos=attr["coord"])
                    if alu in self.__network.nodes():
                        src_node = alu
                    else:
                        raise self.InvalidConfigError(alu + " is not exist")
                else:
                    raise self.InvalidConfigError("missing coordinate of ALU connected to " + dst)


            elif attr["type"] == "SE": # add edge from SE
                if attr["id"] is None or attr["coord"] is None or attr["src_name"] is None:
                    raise self.InvalidConfigError("missing id, coordinate, or src name of SE connected to " + dst)
                else:
                    se = SE_node_exp.format(pos=attr["coord"], id=attr["id"], name=attr["src_name"])
                    if se in self.__network.nodes():
                        src_node = se
                    else:
                        raise self.InvalidConfigError(se + " is not exist")


            elif attr["type"] == "Const": # add edge from const reg
                if attr["index"] is None:
                    raise self.InvalidConfigError("missing index of const register connected to " + dst)
                else:
                    if attr["index"] in self.__const_reg_range:
                        src_node = CONST_node_exp.format(index=attr["index"])
                    else:
                        raise self.InvalidConfigError(str(attr["index"]) + " is out of range for const registers")


            elif attr["type"] == "IN_PORT": # add edge from Input Port
                if attr["index"] is None:
                    raise self.InvalidConfigError("missing index of input port connected to " + dst)
                else:
                    if attr["index"] in self.__in_port_range:
                        src_node = IN_PORT_node_exp.format(index=attr["index"])
                    else:
                        raise self.InvalidConfigError(str(attr["index"]) + " is out of range for input port")
            else:
                raise self.InvalidConfigError("known connection type {0}".format(attr["type"]))

            # add edge and config table entry
            self.__network.add_edge(src_node, dst, weight = attr["weight"])
            self.__reg_config_net_table(dst, src_node, attr["conf_value"])
            # save the init weight value to restore
            self.__link_weight[(src_node, dst)] = attr["weight"]

    def __coord_str2tuple(self, s):
        """convert a string of 2D coordinate to a tuple
        """
        try:
            (x, y) = tuple([int(v) for v in s.strip("()").split(",")])
        except ValueError:
            raise self.InvalidConfigError("Invalid PE coordinate " + s)

        if x < 0 or x >= self.__width or y < 0 or y >= self.__height:
            raise self.InvalidConfigError("Coordinate " + s + " is out of range")
        return (x, y)

    def __parse_input(self, dst, input_connection):
        """Parses Input XML elements.

            Args:
                dst (str): destionation node name
                input_connection (XML Element): an input to dst node

            Returns:
                dict: Parsed items.
        """
        # get connection name
        label = input_connection.get("name")
        if label is None:
            raise self.InvalidConfigError("missing input name connected to " + dst)

        # get connection type
        con_type = input_connection.get("type")
        if con_type is None:
            raise self.InvalidConfigError("missing connection type connected to" + dst)

        # get coord of input_connection (if any)
        coord_str = input_connection.get("coord")
        if not coord_str is None:
            src_coord = self.__coord_str2tuple(coord_str)
        else:
            src_coord = None

        # get index of input_connection (if any)
        index_str = input_connection.get("index")
        if not index_str is None:
            try:
                src_index = int(index_str)
            except ValueError:
                raise ValueError("Invalid index of " + dst + ": " + index_str)
        else:
            src_index = None

        # get id of input_connection (if any)
        id_str = input_connection.get("id")
        if not id_str is None:
            try:
                src_id = int(id_str)
            except ValueError:
                raise ValueError("Invalid id of " + dst + ": " + id_str)
        else:
            src_id = None

        # get src_name of input_connection (if any)
        src_name = input_connection.get("src_name")

        # get link weight
        weight_str = input_connection.get("weight")
        if not weight_str is None:
            try:
                weight = float(weight_str)
            except ValueError:
                raise ValueError("Invalid link weight value of " + weight_str)
        else:
            weight = DEFAULT_EDGE_WEIGHT[con_type]

        # get configuration value
        #   config value is essential except for OUT_PORTs
        conf_val_str = input_connection.get("value")
        if not conf_val_str is None:
            try:
                conf_val = int(conf_val_str)
            except ValueError:
                raise ValueError("Invalid configuration value for input " + label + " for " + \
                                    dst + ": ", conf_val_str)
        elif not self.isOUT_PORT(dst):
            raise self.InvalidConfigError("missing configuration value for input " + \
                                            label + " for " + dst)
        else:
            conf_val = 0

        return {"label": label, "type": con_type, "coord": src_coord, \
                "index": src_index, "id": src_id, "src_name": src_name,\
                "conf_value": conf_val, "weight": weight}


    # getter method
    def getArchName(self):
        '''Returns architecture name of this model

        Args:
            None

        Return:
            str: architecture name
        '''
        return self.__arch_name

    def getNetwork(self):
        '''Returns a networkx object as the PE array model

        Args:
            None

        Return:
            networkx DiGraph: PE array network
        '''
        return copy.deepcopy(self.__network)

    def getNodeName(self, etype, pos=None, index=None, se_id=None, link_name=None):
        '''Returns a node name of PE array network

        Args:
            etype (str): type of the element
                Available types are "ALU", "SE", "Const", "IN_PORT" and "OUT_PORT"
            pos (tuple-like): position of the element)
                It is necessary for "ALU" and "SE"
            index (int): index of some elements
                Its is necessary for "Const", "IN_PORT" and "OUT_PORT"
            se_id (int): id of the SE Elements
            link_name (str): name of output link name of the SE

        Return:
            str: the node name if exist
                if not exist, returns null string
        '''
        if etype == "ALU" and not pos is None:
            node_name = ALU_node_exp.format(pos=pos)
        elif etype == "SE" and not pos is None and \
            not id is None and not link_name is None:
            node_name = SE_node_exp.format(pos=pos, id=se_id, name=link_name)
        elif etype == "Const" and not index is None:
            node_name = CONST_node_exp.format(index=index)
        elif etype == "IN_PORT" and not index is None:
            node_name = IN_PORT_node_exp.format(index=index)
        elif etype == "OUT_PORT" and not index is None:
            node_name = OUT_PORT_node_exp.format(index=index)
        else:
            raise ValueError("Known node type: " + etype)

        if self.__network.has_node(node_name):
            return node_name
        else:
            raise TypeError(node_name + " does not exist")


    def setInitEdgeAttr(self, attr_name, attr, edge_type = None):
        """ Set initial attributes to edges in the network model.

            Args:
                attr_name (str): a name of the attr
                    it is used as a attribute name of networkx digraph
                attr (int): attr value
                edge_type (str): edge type
                    if it is None, all edges are initilized with the value.
                    The type name must be the same name as the Element name,
                    and edge type is same as that of the predecessor node element.

            Returns:
                None
        """

        if edge_type is None:
            nx.set_edge_attributes(self.__network, attr, attr_name)
        else:
            if edge_type == "ALU":
                edges = {(u, v): {attr_name: attr} for u, v in self.__network.edges() if u.find("ALU") == 0}
            elif edge_type == "SE":
                edges = {(u, v): {attr_name: attr} for u, v in self.__network.edges() if u.find("SE") == 0}
            elif edge_type == "Const":
                edges = {(u, v): {attr_name: attr} for u, v in self.__network.edges() if u.find("CONST") == 0}
            elif edge_type == "IN_PORT":
                edges = {(u, v): {attr_name: attr} for u, v in self.__network.edges() if u.find("IN_PORT") == 0}
            elif edge_type == "OUT_PORT":
                edges = {(u, v): {attr_name: attr} for u, v in self.__network.edges() if v.find("OUT_PORT") == 0}

            nx.set_edge_attributes(self.__network, edges)

    def getBBdomains(self):
        """Returns body bias domains of the PE array.

            Args: None

            Returns:
                dictionary: body bias domain information
                    keys: domain name
                    values: PE positions in the domain
        """
        return self.__bb_domains

    def getSize(self):
        """ Returns PE array size.

            Args: None

            Returns:
                tuple: width, height of the PE array
        """

        return (self.__width, self.__height)

    def getLinkWeight(self, edge):
        return self.__link_weight[edge]

    def getConstRegs(self):
        """Returns const register names of the network.
        """
        return [CONST_node_exp.format(index=i) for i in self.__const_reg_range]

    def getInputPorts(self):
        """Returns input port names of the network.
        """
        return [IN_PORT_node_exp.format(index=i) for i in self.__in_port_range]

    def getOutputPorts(self):
        """Returns output port names of the network.
        """
        return [OUT_PORT_node_exp.format(index=i) for i in self.__in_port_range]

    def getInoutPorts(self):
        """Returns pairs of input port and output port
        """
        if self.__inout_used:
            return [(IN_PORT_node_exp.format(index=i), OUT_PORT_node_exp.format(index=i)) \
                     for i in self.__in_port_range]
        else:
            return []

    def getInputPortsByPos(self, pos):
        """Returns input port names at the specified pos of the network.

            Args:
                pos (str): position of input ports as following:
                    "left", "right", "top", "bottom"
        """
        if pos in self.__input_pos:
            return [IN_PORT_node_exp.format(index=i) \
                    for i in self.__input_pos[pos]]
        else:
            return []

    def getOutputPortsByPos(self, pos):
        """Returns output port names at the specified pos of the network.

            Args:
                pos (str): position of output ports as following:
                    "left", "right", "top", "bottom"
        """
        if pos in self.__output_pos:
            return [OUT_PORT_node_exp.format(index=i) \
                    for i in self.__output_pos[pos]]
        else:
            return []



    def get_PE_resources(self, coord):
        return {"ALU": self.getNodeName("ALU", coord),\
                 "SE": self.__se_lists[coord]}

    def getPregPositions(self):
        return self.__preg_positions


    def getFreeSEs(self, routed_graph, x_range=None, y_range=None):
        """Gets unused SEs.

            Args:
                routed_graph (networkx graph): routed graph
                Optional:
                    x_range (range): width range
                    y_range (range): column range

            Reterns:
                list: unused SEs
        """

        rtn_list = []

        # check range
        if x_range is None:
            x_range = range(self.__width)
        if y_range is None:
            y_range = range(self.__height)

        for x in x_range:
            for y in y_range:
                se_set = set([se for subset in self.__se_lists[(x, y)].values() for se in subset])
                for se in se_set:
                    if self.__network.nodes[se]["free"] == True:
                        rtn_list.append(se)

        return rtn_list

    def getStageDomains(self, preg_config, remove_return_se = False):
        """Gets resources for each pipeline stage

            Args:
                preg_config (list of Boolean): pipeline register configuration
                                               if n-th value is True, n-th preg is activated

                Optional
                    remove_return_se (Boolean): eliminates return only SE except for last stage
                                        default: False

            Returns:
                list: resources for each pipeline stage
                        1st index is to specify the stage
                        2nd index is to specify the resource node
        """
        stage = 0
        rtn_list = [[] for stage in range(sum(preg_config) + 1)]

        # activated preg positions
        active_preg_positions = [self.__preg_positions[i] for i in range(len(self.__preg_positions)) if preg_config[i] == True]

        # get nodes for each stage
        se_set = set()
        for y in range(self.__height):
            if stage < len(active_preg_positions):
                if active_preg_positions[stage] <= y:
                    stage += 1
            # add ALU
            rtn_list[stage].extend([ALU_node_exp.format(pos=(x, y)) for x in range(self.__width)])
            # add SE
            for x in range(self.__width):
                se_set = set([se for subset in self.__se_lists[(x, y)].values() for se in subset])
                rtn_list[stage].extend([se for se in se_set if not se in self.__return_only_se])
        else:
            if remove_return_se:
                rtn_list[-1].extend(list(set(self.__return_only_se) & se_set))
            else:
                rtn_list[-1].extend(self.__return_only_se)

        return rtn_list

    def getPregNumber(self):
        """Returns pipeline register number of the architecture
        """
        return len(self.__preg_positions)

    def isNeedConstRoute(self):
        """Returns whether const routing is needed
        """

        return not self.__infini_const

    def isIOShared(self):
        """Returns whether inout port is used instead of input/output port
        """

        return self.__inout_used

    def isHeteroISA(self):
        """Returns heterogeneity of ISA
        """

        return self.__heteroISA

    def getSupportedOps(self):
        """Returns supported operations
        """

        return list(self.__supported_ALU.keys())

    def getSupportedALUs(self, opcode):
        """Returns ALU list supporting the specified opcode
        """
        try:
            return self.__supported_ALU[opcode]
        except KeyError:
            return []

    @staticmethod
    def isSE(node_name):
        """Check whether the node is SE or not.

            Args:
                node_name (str): a name of node

            Returns:
                bool: if the node is SE, return True.
                      otherwise return False.

        """
        return node_name.find("SE") == 0


    @staticmethod
    def isALU(node_name):
        """Check whether the node is SE or not.

            Args:
                node_name (str): a name of node

            Returns:
                bool: if the node is ALU, return True.
                      otherwise return False.

        """
        return node_name.find("ALU") == 0

    @staticmethod
    def isOUT_PORT(node_name):
        """Check whether the node is OUT_PORT or not.

            Args:
                node_name (str): a name of node

            Returns:
                bool: if the node is OUT_PORT, return True.
                      otherwise return False.

        """
        return node_name.find("OUT_PORT") == 0

    @staticmethod
    def isIN_PORT(node_name):
        """Check whether the node is OUT_PORT or not.

            Args:
                node_name (str): a name of node

            Returns:
                bool: if the node is OUT_PORT, return True.
                      otherwise return False.

        """
        return node_name.find("IN_PORT") == 0

    def getOperationList(self, coord):
        """Returns operation list supported by an ALU.

            Args:
                coord (int, int): a coordinate of the ALU.

            Returns:
                list: the operation list.
                      If the coordinate is out of range, return empty list.
        """
        (x, y) = coord
        if x < 0 or x >= self.__width or y < 0 or y >= self.__height:
            return []
        else:
            return self.__operation_list[x][y]

    def getOpConfValue(self, coord, opcode):
        """Gets configration value of ALU

            Args:
                coord (tuple): coordinate of the ALU
                opcode (str): opcode assigned to the ALU

            Returns:
                int: configration value
        """
        x, y = coord
        return self.__config_op_table[x][y][opcode]

    def getNetConfValue(self, dst, src):
        """Gets configration value of SE

            Args:
                dst: a node of SE output channel
                src: a node connected to the output

            Returns:
                int: configration value
        """
        return self.__config_net_table[dst][src]

    def getALUMuxCount(self, coord):
        """Gets mux count of the ALU

            Args:
                coord (tuple): coordinate of the ALU

            Returns:
                int: the maximum number of inputs for the ALU
        """
        x, y = coord
        return self.__mux_count[x][y]

    def getWireName(self, se):
        """Gets an output channel name"""
        return self.__output_names[se]


    def isRoutingALU(self, pos):
        """Checks whether the ALU can work for routing node

            Args:
                pos: coordinate of the ALU

            Returns:
                bool: if the ALU can work for routing node
                      otherwise return False.

        """
        if pos in self.__routing_ALU:
            return True

    def getRoutingOpcode(self, node):
        """Gets opcode for routing

            Args:
                node: node name for ALU

            Returns:
                str: opcode for the routing

        """
        return self.__routing_opcode[node]

