from PEArrayModel import PEArrayModel

DELAY_UNITS = {"ps": 10**(-12), "ns": 10**(-9), "us": 10**(-6), "ms": 10**(-3)}
POWER_UNITS = {"pW": 10**(-12), "nW": 10**(-9), "uW": 10**(-6), "mW": 10**(-3)}
ENERGY_UNITS = {"pJ": 10**(-12), "nJ": 10**(-9), "uJ": 10**(-6), "mJ": 10**(-3)}

class SimParameters():
    class InvalidParameters(Exception):
        pass

    # default units
    units = {"delay": "ns", "power": "mW", "energy": "uJ"}

    def __init__(self, CGRA, data):
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
        op_list = set()
        for x in range(width):
            for y in range(height):
                op_list |= set(CGRA.getOperationList((x, y)))

        # initilize instance variables
        self.delay_info = {op: {} for op in op_list}
        self.delay_info["SE"] = {}
        self.switching_info = {op: 0 for op in op_list}
        self.PE_leak = {}
        self.switching_energy = 0.0
        self.switching_propagation = 0.0
        self.switching_damp = 0.0
        self.bias_range = set()
        if CGRA.getPregNumber() > 0:
            self.preg_dynamic_energy = 0.0
            self.preg_leak = 0.0

        # load each data
        self.__load_bias_range(bias_range)
        self.__load_delay_info(delay_data)
        self.__load_power_info(power_data)

    def __load_bias_range(self, bias_range_xml):
        for bias in bias_range_xml.findall("bias"):
            if bias.text is None:
                raise SimParameters.InvalidParameters("There is no voltage value for bias range")
            try:
                bias_val = float(bias.text)
            except ValueError:
                raise SimParameters.InvalidParameters("Invalid value for bias voltage: " + bias.text)
            self.bias_range.add(bias_val)


    def __load_delay_info(self, delay_xml):
        # read unit for delay time
        unit_str = delay_xml.get("unit")
        if unit_str is None:
            unit_str = DELAY_UNITS[self.units["delay"]]
        if not unit_str in DELAY_UNITS.keys():
            raise SimParameters.InvalidParameters("Unknown unit for dealy: " + unit_str)

        # load delay time of ALU for each opearation
        for alu in delay_xml.findall("ALU"):
            # check bias volatage
            bias_str = alu.get("bias")
            if bias_str is None:
                raise SimParameters.InvalidParameters("missing bias voltage for ALU delay")
            try:
                bias = float(bias_str)
            except ValueError:
                raise SimParameters.InvalidParameters("Invalid value for bias volatage: " + bias_str)
            # check operation
            op_str = alu.get("op")
            if op_str is None:
                raise SimParameters.InvalidParameters("missing operation name for ALU delay")
            if not op_str in self.delay_info.keys():
                raise SimParameters.InvalidParameters("Not supported operation: " + op_str)
            # check delay value
            if not alu.text is None:
                try:
                    delay_val = float(alu.text)
                except ValueError:
                    raise SimParameters.InvalidParameters("Invalid value for delay time: " + alu.text)
            else:
                raise SimParameters.InvalidParameters("missing delay time value for {0} with bias {1} V".format(op_str, bias))

            self.delay_info[op_str][bias] = delay_val * DELAY_UNITS[unit_str] / DELAY_UNITS[self.units["delay"]]

        # load delay time of SE
        for se in delay_xml.findall("SE"):
            bias_str = se.get("bias")
            if bias_str is None:
                raise SimParameters.InvalidParameters("missing bias voltage for SE delay")
            try:
                bias = float(bias_str)
            except ValueError:
                raise SimParameters.InvalidParameters("Invalid value for bias volatage: " + bias_str)
            # check delay value
            if not se.text is None:
                try:
                    delay_val = float(se.text)
                except ValueError:
                    raise SimParameters.InvalidParameters("Invalid value for delay time: " + se.text)
            else:
                raise SimParameters.InvalidParameters("missing delay time value for SE with bias {1} V".format(bias))

            self.delay_info["SE"][bias] = delay_val * DELAY_UNITS[unit_str] / DELAY_UNITS[self.units["delay"]]

        # validate loaded data
        for op in self.delay_info.keys():
            bias_diff = self.bias_range - set(self.delay_info[op].keys())
            if len(bias_diff) > 0:
                raise SimParameters.InvalidParameters("There is no delay time for {0} with bias {1} V".format(\
                                                        op, list(bias_diff)[0]))

    def __load_power_info(self, power_xml):

        # load static power info
        static_power = power_xml.find("Static")
        if static_power is None:
            raise SimParameters.InvalidParameters("There is no static power information")
        for st_power in static_power.findall("PE"):
            unit_str = st_power.get("unit")
            # if not unit specification, use default unit
            if unit_str is None:
                unit_str = POWER_UNITS[self.units["power"]]
            elif not unit_str in POWER_UNITS.keys():
                raise SimParameters.InvalidParameters("Unknown unit for power: " + unit_str)

            # check bias volatage
            bias_str = st_power.get("bias")
            if bias_str is None:
                raise SimParameters.InvalidParameters("missing bias voltage for static power")
            try:
                bias = float(bias_str)
            except ValueError:
                raise SimParameters.InvalidParameters("Invalid value for bias volatage: " + bias_str)

            # check power value
            if not st_power.text is None:
                try:
                    power_val = float(st_power.text)
                except ValueError:
                    raise SimParameters.InvalidParameters("Invalid value for static power: " + st_power.text)
            else:
                raise SimParameters.InvalidParameters("missing static power value with bias {0} V".format(bias))

            self.PE_leak[bias] = power_val * POWER_UNITS[unit_str] / POWER_UNITS[self.units["power"]]

        if not self.preg_leak is None:
            preg_static = static_power.find("PREG")
            unit_str = st_power.get("unit")
            # if not unit specification, use default unit
            if unit_str is None:
                unit_str = POWER_UNITS[self.units["power"]]
            elif not unit_str in POWER_UNITS.keys():
                raise SimParameters.InvalidParameters("Unknown unit for power: " + unit_str)


        # validate static power info
        bias_diff = self.bias_range - set(self.PE_leak.keys())
        if len(bias_diff) > 0:
            raise SimParameters.InvalidParameters("There is static power with bias {0} V".format(list(bias_diff)[0]))

        dynamic_info = power_xml.find("Dynamic")
        if dynamic_info is None:
            raise SimParameters.InvalidParameters("There is no data for dynamic power")


        # load switching energy raise SimParameters.InvalidParameters("")
        E_sw = dynamic_info.find("Energy")
        if E_sw is None:
            raise SimParameters.InvalidParameters("There is no switching energy data")
        # check units
        unit_str = E_sw.get("unit")
        if unit_str is None:
            unit_str = ENERGY_UNITS[self.units["energy"]]
        if not unit_str in ENERGY_UNITS.keys():
            raise SimParameters.InvalidParameters("Unknown unit for energy: " + unit_str)
        if E_sw.text is None:
            raise SimParameters.InvalidParameters("missing energy value for switching")
        try:
            E_sw_val = float(E_sw.text)
        except ValueError:
            raise SimParameters.InvalidParameters("Invalid value for energy: " + E_sw.text)

        self.switching_energy = E_sw_val * ENERGY_UNITS[unit_str] / ENERGY_UNITS[self.units["energy"]]

        # if PE array is pipelined, load preg dynamic energy
        if not self.preg_dynamic_energy is None:

            preg_dyn = dynamic_info.find("PREG")
            if preg_dyn is None:
                raise SimParameters.InvalidParameters("There is no dynamic power data for pipeline register")
            # check units
            unit_str = preg_dyn.get("unit")
            if unit_str is None:
                unit_str = ENERGY_UNITS[self.units["energy"]]
            if not unit_str in ENERGY_UNITS.keys():
                raise SimParameters.InvalidParameters("Unknown unit for energy: " + unit_str)
            if preg_dyn.text is None:
                raise SimParameters.InvalidParameters("missing energy value for pipeline register")
            try:
                preg_dyn_val = float(preg_dyn.text)
            except ValueError:
                raise SimParameters.InvalidParameters("Invalid value for energy: " + preg_dyn.text)

            self.preg_dynamic_energy = preg_dyn_val * ENERGY_UNITS[unit_str] / ENERGY_UNITS[self.units["energy"]]

        # load propagation ratio
        prop = dynamic_info.find("Propagation")
        if prop is None:
            raise SimParameters.InvalidParameters("There is no specification of propagation ratio")
        if prop.text is None:
            raise SimParameters.InvalidParameters("missing value for propagation ratio")
        try:
            prop_val = float(prop.text)
        except ValueError:
                raise SimParameters.InvalidParameters("Invalid value: " + prop.text)
        self.switching_propagation = prop_val

        # load damp ratio
        damp = dynamic_info.find("Damp")
        if damp is None:
            raise SimParameters.InvalidParameters("There is no specification of damp ratio")
        if damp.text is None:
            raise SimParameters.InvalidParameters("missing value for damp ratio")
        try:
            damp_val = float(damp.text)
        except ValueError:
                raise SimParameters.InvalidParameters("Invalid value: " + damp.text)
        self.switching_damp = damp_val

        # load switching count for each operation
        for sw in dynamic_info.findall("Switching"):
            op_str = sw.get("op")
            if op_str is None:
                raise SimParameters.InvalidParameters("missing operation for switching count")
            if not op_str in self.switching_info.keys():
                raise SimParameters.InvalidParameters("Not supported operation: " + op_str)
            if sw.text is None:
                raise SimParameters.InvalidParameters("missing switching value for " + op_str)
            try:
                sw_val = float(sw.text)
            except ValueError:
                    raise SimParameters.InvalidParameters("Invalid switching value: " + sw.text)
            self.switching_info[op_str] = sw_val

    def calc_power(self, t, energy):
        return  energy * ENERGY_UNITS[self.units["energy"]] \
                   / t / DELAY_UNITS[self.units["delay"]] / POWER_UNITS[self.units["power"]]


# test
if __name__ == "__main__":
    import xml.etree.ElementTree as ET
    tree = ET.ElementTree(file="./CMA_conf.xml")
    pearray = tree.getroot()
    if pearray.tag == "PEArray":
        model = PEArrayModel(pearray)

    try:
        tree = ET.ElementTree(file="./simdata.xml")
    except ET.ParseError as e:
        print("Parse Error", e.args)
        exit()

    data = tree.getroot()
    simParams = SimParameters(model, data)