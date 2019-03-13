from PEArrayModel import PEArrayModel

DELAY_UNITS = {"ps": 10**(-12), "ns": 10**(-9), "us": 10**(-6), "ms": 10**(-3)}
POWER_UNITS = {"pW": 10**(-12), "nW": 10**(-9), "uW": 10**(-6), "mW": 10**(-3)}
ENERGY_UNITS = {"pJ": 10**(-12), "nJ": 10**(-9), "uJ": 10**(-6), "mJ": 10**(-3)}
UNIT_DICTS = {"delay": DELAY_UNITS, "power": POWER_UNITS, "energy": ENERGY_UNITS}


class SimParameters():
    class InvalidParameters(Exception):
        pass

    # default units
    units = {"delay": "ns", "power": "mW", "energy": "uJ"}

    def __init__(self, CGRA, data):
        """ Constructor of this class

            Args:
                CGRA (PEArrayModel): A model of the CGRA
                data (XML Element): simluation parameters

            Raise:
                If there exist invalid parameters, or lack of information,
                it will raise InvalidParameters.

        """
        # find bias range element
        bias_range = data.find("BiasRange")
        if bias_range is None:
            raise TypeError("There is no specification of bias range")
        # find delay data element
        delay_data = data.find("Delay")
        if delay_data is None:
            raise TypeError("There is no delay information")
        # find power data element
        power_data = data.find("Power")
        if power_data is None:
            raise TypeError("There is no power information")

        # get all supported operations
        (width, height) = CGRA.getSize()
        self.op_list = set()
        for x in range(width):
            for y in range(height):
                self.op_list |= set(CGRA.getOperationList((x, y)))

        # initilize instance variables
        self.delay_info = {op: {} for op in self.op_list}
        self.delay_info["SE"] = {}
        self.PE_leak = {}
        self.switching_info = {op: 0 for op in self.op_list}
        self.switching_energy = 0.0
        self.switching_propagation = 0.0
        self.switching_decay = 0.0
        self.bias_range = set()
        if CGRA.getPregNumber() > 0:
            self.preg_dynamic_energy = 0.0
            self.preg_leak = 0.0

        self.se_weight = 1.0

        # load each data
        self.__load_bias_range(bias_range)
        self.__load_delay_info(delay_data)
        self.__load_power_info(power_data)

    def __load_bias_range(self, bias_range_xml):
        """Loads body bias range.

            Args:
                bias_range_xml (XML Element): Body bias range

            Raise:
                If there exist invalid parameters, or lack of information,
                it will raise InvalidParameters.

        """
        for bias in bias_range_xml.findall("bias"):
            if bias.text is None:
                raise SimParameters.InvalidParameters("There is no voltage value for bias range")
            try:
                bias_val = float(bias.text)
            except ValueError:
                raise SimParameters.InvalidParameters("Invalid value for bias voltage: " + bias.text)
            self.bias_range.add(bias_val)

        if len(self.bias_range) == 0:
            raise SimParameters.InvalidParameters("At least, zero bias must be included in bias range")


    def __load_delay_info(self, delay_xml):
        """Loads delay information.

            Args:
                delay_xml (XML Element): Delay information

            Raise:
                If there exist invalid parameters, or lack of information,
                it will raise InvalidParameters.
        """

        # read unit for delay time
        d_unit = self.__getUnit(delay_xml, "delay")

        # load delay time of ALU for each opearation
        for alu in delay_xml.findall("ALU"):
            # check bias volatage
            bias = self.__getBias(alu, msg="for ALU delay")

            # check operation
            op_str = self.__getOp(alu, msg="for ALU delay")

            # check delay value
            delay_val = self.__getFloat(alu, msg=["delay", "{0} with bias {0}".format(op_str, bias)])

            # store
            self.delay_info[op_str][bias] = delay_val * d_unit / DELAY_UNITS[self.units["delay"]]

        # load delay time of SE
        for se in delay_xml.findall("SE"):
            #check bias volatage
            bias = self.__getBias(se, msg="for ALU delay")

            # check delay value
            delay_val = self.__getFloat(se, msg=["delay", "for SE with bias " + str(bias) + "V"])

            # store
            self.delay_info["SE"][bias] = delay_val * d_unit / DELAY_UNITS[self.units["delay"]]

        # validate loaded data
        for op in self.delay_info.keys():
            # PE
            bias_diff = self.bias_range - set(self.delay_info[op].keys())
            if len(bias_diff) > 0:
                raise SimParameters.InvalidParameters("There is no delay time for {0} with bias {1} V".format(\
                                                        op, list(bias_diff)[0]))
        # SE
        bias_diff = self.bias_range - set(self.delay_info["SE"].keys())
        if len(bias_diff) > 0:
            raise SimParameters.InvalidParameters("There is no delay time for SE with bias {0} V".format(list(bias_diff)[0]))

    def __load_power_info(self, power_xml):
        """Loads power information.

            Args:
                power_xml (XML Element): Power information

            Raise:
                If there exist invalid parameters, or lack of information,
                it will raise InvalidParameters.
        """

        # load static power info
        static_powers = power_xml.find("Static")
        if static_powers is None:
            raise SimParameters.InvalidParameters("There is no static power information")

        # load PE static power
        for st_power in static_powers.findall("PE"):
            # check power unit
            p_unit = self.__getUnit(st_power, "power")

            # check bias volatage
            bias = self.__getBias(st_power, "for PE static power")

            # check power value
            power_val = self.__getFloat(st_power, msg=["static power", "PE with bias" + str(bias) + "V"])

            # store
            self.PE_leak[bias] = power_val * p_unit / POWER_UNITS[self.units["power"]]

        # load PREG static power
        if not self.preg_leak is None:
            preg_static = static_powers.find("PREG")
            #check power unit
            p_unit = self.__getUnit(preg_static, "power")

            # check power value
            power_val = self.__getFloat(preg_static, msg=["static power", "PREG"])

            #store
            self.preg_leak = power_val * p_unit / POWER_UNITS[self.units["power"]]


        # validate static power info
        bias_diff = self.bias_range - set(self.PE_leak.keys())
        if len(bias_diff) > 0:
            raise SimParameters.InvalidParameters("There is static power with bias {0} V".format(list(bias_diff)[0]))

        # get dynamic power information
        dynamic_info = power_xml.find("Dynamic")
        if dynamic_info is None:
            raise SimParameters.InvalidParameters("There is no data for dynamic power")

        # load switching energy
        E_sw = dynamic_info.find("Energy")
        if E_sw is None:
            raise SimParameters.InvalidParameters("There is no switching energy data")

        # check units
        e_unit = self.__getUnit(E_sw, "energy")

        # check energy value
        energy_val = self.__getFloat(E_sw, msg=["dynamic energy", "PE"])

        # store
        self.switching_energy = energy_val * e_unit / ENERGY_UNITS[self.units["energy"]]

        # if PE array is pipelined, load preg dynamic energy
        if not self.preg_dynamic_energy is None:

            preg_dyn = dynamic_info.find("PREG")
            if preg_dyn is None:
                raise SimParameters.InvalidParameters("There is no dynamic power data for pipeline register")
            # check units
            e_unit = self.__getUnit(preg_dyn, "energy")

            # check energy value
            energy_val = self.__getFloat(preg_dyn, msg=["dynamic energy", "PREG"])

            # store
            self.preg_dynamic_energy = energy_val * e_unit / ENERGY_UNITS[self.units["energy"]]

        # load propagation ratio
        prop = dynamic_info.find("Propagation")
        if prop is None:
            raise SimParameters.InvalidParameters("There is no specification of propagation ratio")
        # check propagation value
        prop_val = self.__getFloat(prop, msg=["propagation", "glitch estimation"])
        # store
        self.switching_propagation = prop_val

        # load decay ratio
        decay = dynamic_info.find("Decay")
        # check decay value
        decay_val = self.__getFloat(decay, msg=["decay", "glitch estimation"])
        # store
        self.switching_decay = decay_val

        # load se weight
        se_w = dynamic_info.find("SE_weight")
        # check se_w value
        se_w_val = self.__getFloat(se_w, msg=["se_w", "glitch estimation"])
        # store
        self.se_weight = se_w_val

        # load switching count for each operation
        for sw in dynamic_info.findall("Switching"):
            # get operation name
            op_str = self.__getOp(sw, "for switching count")
            # check switcing value
            sw_val = self.__getFloat(sw, msg=["switching", op_str])
            # store
            self.switching_info[op_str] = sw_val

    def calc_power(self, delay, energy):
        """Caluculate power consumption from delay and energy.

            Args:
                delay (float): delay time
                energy (float): energy

            Returns:
                float: power consumption.
        """
        return  energy * ENERGY_UNITS[self.units["energy"]] \
                   / delay / DELAY_UNITS[self.units["delay"]] / POWER_UNITS[self.units["power"]]

    def change_unit_scale(self, unit_type, unit):
        """Change scale of a unit.

            Args:
                unit_type (str): unit type
                    "delay", "power", "energy" are available
                unit (str): unit to be set

            Returns: None

            Raise:
                If there is some error, it will raise ValueError
        """
        if unit_type == "delay":
            if not unit in DELAY_UNITS.keys():
                ValueError("Invalid delay unit: " + unit)
            # update value
            scale = DELAY_UNITS[self.units["delay"]] / DELAY_UNITS[unit]
            for k in self.delay_info.keys():
                for bias in self.delay_info[k].keys():
                    self.delay_info[k][bias] *= scale
            # update unit
            self.units["delay"] = unit

        elif unit_type == "power":
            if not unit in POWER_UNITS.keys():
                ValueError("Invalid power unit: " + unit)
            # update value
            scale = POWER_UNITS[self.units["power"]] / POWER_UNITS[unit]
            for bias in self.PE_leak.keys():
                self.PE_leak[bias] *= scale
            if not self.preg_leak is None:
                self.preg_leak *= scale
            # update unit
            self.units["power"] = unit


        elif unit_type == "energy":
            if not unit in ENERGY_UNITS.keys():
                ValueError("Invalid energy unit: " + unit)
            # update value
            scale = ENERGY_UNITS[self.units["energy"]] / ENERGY_UNITS[unit]
            self.switching_energy *= scale
            if not self.preg_dynamic_energy is None:
                self.preg_dynamic_energy *= scale
            # update unit
            self.units["energy"] = unit
        else:
            raise ValueError("Unknown unit type: " + unit_type)


    def __getUnit(self, element, unit_type):
        """Gets unit attribute from an element

            Args:
                element(XML element): an XML element containing unit attribute
                unit_type(str): unit type
                    "delay", "power", "energy" are available

            Return:
                int: digits of the unit
        """
        unit_str = element.get("unit")
        if unit_str is None:
            # use default unit
            unit_str = self.units[unit_type]
        if not unit_str in UNIT_DICTS[unit_type].keys():
            raise SimParameters.InvalidParameters("Unknown unit for {0}: {1}".format(unit_type, unit_str))

        return UNIT_DICTS[unit_type][unit_str]

    def __getBias(self, element, msg=""):
        """Gets bias attribute from an element

            Args:
                element(XML element): an XML element containing bias attribute
                msg(str): a message which is used if bias value is missing
                    It follows a message "missing bias voltage"

            Return:
                float: bias volatage
        """
        bias_str = element.get("bias")
        if bias_str is None:
            raise SimParameters.InvalidParameters("missing bias voltage " + msg)
        try:
            bias = float(bias_str)
        except ValueError:
            raise SimParameters.InvalidParameters("Invalid value for bias volatage: " + bias_str)

        return bias

    def __getOp(self, element, msg=""):
        """Gets opcode attribute from an element

            Args:
                element(XML element): an XML element containing opcode attribute
                msg(str): a message which is used if opcode is missing
                    It follows a message "missing operation name"

            Return:
                str: operation name
        """
        op_str = element.get("op")
        if op_str is None:
            raise SimParameters.InvalidParameters("missing operation name " + msg)
        if not op_str in self.op_list:
            raise SimParameters.InvalidParameters("Not supported operation: " + op_str)

        return op_str

    def __getFloat(self, element, msg=["", ""]):
        """Gets bias attribute from an element

            Args:
                element(XML element): an XML element containing bias attribute
                msg(list of str): two messages which are used if any error occurs
                    In case of missing element, print
                        "missing (1st message) value for (2nd message)".
                    In case of invalid value, print
                        "Invalid value (inner text) for (1st message)"

            Return:
                float: inner value
        """
        if element is None:
            raise SimParameters.InvalidParameters("missing {0[0]} value for {0[1]}".format(msg))
        else:
            try:
                float_val = float(element.text)
            except ValueError:
                raise SimParameters.InvalidParameters("Invalid value {0} for {1[0]}".format(element.text, msg))

            return float_val

    def getTimeUnit(self):
        return self.units["delay"]
