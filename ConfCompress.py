import pulp
import re
import math
import copy

from PEArrayModel import PEArrayModel

class ConfCompressor(object):
    """docstring for Compressor"""
    def __init__(self, CGRA, conf_formats, conf_data):
        self.__arch = CGRA
        (self.__width, self.__height) = self.__arch.getSize()
        self.__conf_formats = conf_formats
        self.__espresso_enabled = True
        self.__init_write_table = [[{element: False if element in conf_data[x][y].keys() else True\
                                for element in conf_formats.keys()}\
                                for y in range(self.__height)] for x in range(self.__width)]
        self.__write_table = None
        self.__conf_data = conf_data
        # fill unused fields
        for x in range(self.__width):
            for y in range(self.__height):
                self.__conf_data[x][y].update({field: 0 for field in \
                            set(conf_formats.keys() - set(self.__conf_data[x][y].keys()))})
        # for truth table
        self.__col_bitwidth = math.ceil(math.log2(self.__width))
        self.__row_bitwidth = math.ceil(math.log2(self.__height))

        try:
            from pyeda.inter import exprvars
            from pyeda.inter import truthtable
            from pyeda.inter import espresso_tts
        except ImportError:
            self.__espresso_enabled = False


    def __writable(self, coord, conf):
        """Check if the conf data can be written to the PE

        Args:
            coord(tuple): coordinate of the PE
            conf: dict of configuration data (key: field, value: data)

        Returns:
            bool: if the data can be written, return True
        """
        (x, y) = coord
        for k, v in conf.items():
            # already another data is fixed
            if self.__conf_data[x][y][k] != v and \
                self.__write_table[x][y][k]:
                return False
        return True

    def __effective_bits(self, coord, conf):
        """Analyzes how many bit field will be fixed by writing the conf data

            Args:
                coord(tuple): coordinate of the PE
                conf: dict of configuration data (key: field, value: data)

            Returns:
                int: effective bit count by the writing
        """
        ret_val = 0
        (x, y) = coord
        for k, v in conf.items():
            if self.__conf_data[x][y][k] == v and \
                self.__write_table[x][y][k] == False:
                ret_val += self.__conf_formats[k]
        return ret_val

    def __isFixed(self, coord):
        """Check if all configuration fields of the PE are fixed

            Args:
                coord(tuple): coordinate of the PE

            Returns:
                bool: if configration of the PE is fixed, return True
        """

        (x, y) = coord
        return all(self.__write_table[x][y].values())

    def __update(self, coord, conf):
        """update configuration data of the PE

            Args:
                coord(tuple): coordinate of the PE
                conf: dict of configuration data (key: field, value: data)

        """
        (x, y) = coord
        for k, v in conf.items():
            if self.__conf_data[x][y][k] == v:
                self.__write_table[x][y][k] = True


    def compress_fine_grain_ILP(self, max_bitwidth):

        max_pattern = dict()

        max_pattern = {"score": -1.0, "rows": list(), "cols": [0 for x in range(12)], "conf": list()}


        match_list = list()

        for conf in conf_list:
            for y in range(height):
                for x in range(width):
                    ef_bits = pearray[x][y].__effective_bits(base_pe, [conf])
                    if ef_bits != 0:
                        match_list.append((conf, x, y, ef_bits))


        problem = pulp.LpProblem('Problem Name', pulp.LpMaximize) 
        rows = pulp.LpVariable.dicts('rows', range(height), 0, 1, cat = 'Binary')
        cols = pulp.LpVariable.dicts('cols', range(width), 0, 1, cat = 'Binary')
        conf_sel = pulp.LpVariable.dicts('conf_sel', conf_list, 0, 1, cat = 'Binary')
        flag = pulp.LpVariable.dicts('flag', (conf_sel, range(width), range(height)), 0, 1, cat = 'Binary')

        # objective
        problem += pulp.lpSum([flag[conf][x][y] * val \
                               for conf, x, y, val in match_list])

        # Constraints
        for conf in conf_list:
            for x in range(width):
                for y in range(height):
                    if pearray[x][y].not_mappable(base_pe, [conf]):
                        problem += flag[conf][x][y] == 0

                    problem += flag[conf][x][y] >= conf_sel[conf] + cols[x] + rows[y] - 2
                    problem += 3 * flag[conf][x][y] <= conf_sel[conf] + cols[x] + rows[y]


        problem += pulp.lpSum([bit_width[conf]  * conf_sel[conf] for conf in conf_list]) <= MAX_WIDTH

        stat = problem.solve()
        result = problem.objective.value()

        if pulp.LpStatus[stat] == "Optimal" and result != None:
            if result >= max_pattern["score"]:
                max_pattern["score"] = result
                max_pattern["rows"] = [0 if rows[y].value() == None else int(rows[y].value()) for y in range(height)]
                max_pattern["cols"] = [0 if cols[x].value() == None else int(cols[x].value()) for x in range(width)]
                max_pattern["conf"] = list()
                for conf in conf_list:
                    if conf_sel[conf].value() != None and \
                                          int(conf_sel[conf].value()) == 1:
                        max_pattern["conf"].append(conf)


        return max_pattern

    def compress_coarse_grain_ILP(self, operand_pattern_list):
        """compress the configuration data using Espresso

            Args:
                operand_pattern_list (list): list of multicasted field pattern

            Returns:
                list of dict: sequential multicasting data
                    keys and values of dict:
                        rows: bitmap of rows
                        cols: bitmap of columns
                        conf: dict of configuration data (key: field, value: data)

        """
        self.__write_table = copy.deepcopy(self.__init_write_table)
        width = self.__width
        height = self.__height

        romultic_data = []

        while True:
            max_pattern = {"score": -1.0, "rows": list(), "cols": [0 for x in range(width)], "conf": list()}

            # analyze unfixed PEs
            unfixed_PEs = [(x,y) for x in range(width) for y in range(height)\
                                if not self.__isFixed((x,y))]

            if len(unfixed_PEs) == 0:
                break
            # enumerate conf pattern
            target_confs = []
            for (x,y) in unfixed_PEs:
                for operand_pattern in operand_pattern_list:
                    if any([field in self.__conf_data[x][y] for field in operand_pattern]):
                        conf = {field: self.__conf_data[x][y][field] if field in self.__conf_data[x][y] else 0\
                                 for field in operand_pattern}
                        if not conf in target_confs:
                            target_confs.append(conf)

            # search for best multicasting data
            for conf in target_confs:
                match_list = list()

                # get coefficients for ILP formulation
                for y in range(height):
                    for x in range(width):
                        ef_bits = self.__effective_bits((x,y), conf)
                        if ef_bits != 0:
                            match_list.append((x, y, ef_bits))

                # define ILP problem
                problem = pulp.LpProblem('Find best bit-maps', pulp.LpMaximize)
                rows = pulp.LpVariable.dicts('rows', range(height), 0, 1, cat = 'Binary')
                cols = pulp.LpVariable.dicts('cols', range(width), 0, 1, cat = 'Binary')
                flag = pulp.LpVariable.dicts('flag', (range(width), range(height)), 0, 1, cat = 'Binary')

                # set objective
                problem += pulp.lpSum([flag[x][y] * val \
                                       for  x, y, val in match_list])

                # Constraints
                for x in range(width):
                    for y in range(height):
                        if not self.__writable((x,y), conf):
                            problem += flag[x][y] == 0

                        # logical AND is linearized
                        problem += flag[x][y] >= cols[x] + rows[y] - 1
                        problem += 2 * flag[x][y] <= cols[x] + rows[y]

                # solve the problem
                stat = problem.solve()
                result = problem.objective.value()

                if pulp.LpStatus[stat] == "Optimal" and result != None:
                    if result >= max_pattern["score"]:
                        max_pattern["score"] = result
                        max_pattern["rows"] = [0 if rows[y].value() == None else int(rows[y].value()) for y in range(height)]
                        max_pattern["cols"] = [0 if cols[x].value() == None else int(cols[x].value()) for x in range(width)]
                        max_pattern["conf"] = conf

            # update
            for x in range(width):
                if max_pattern["cols"][x] == 1:
                    for y in range(height):
                        if max_pattern["rows"][y] == 1:
                            self.__update((x,y), max_pattern["conf"])

            romultic_data.append(max_pattern)

        return romultic_data


    def compress_espresso(self, operand_pattern_list):
        """compress the configuration data using Espresso

            Args:
                operand_pattern_list (list): list of multicasted field pattern

            Returns:
                list of dict: sequential multicasting data
                    keys and values of dict:
                        rows: bitmap of rows
                        cols: bitmap of columns
                        conf: dict of configuration data (key: field, value: data)

            Raises:
                RuntimeError
        """
        if not self.__espresso_enabled:
            raise RuntimeError("Cannot import PyEDA. Please install it by \"pip3 install pyeda\"")

        # import needed modules
        from pyeda.inter import exprvars
        from pyeda.inter import truthtable
        from pyeda.inter import espresso_tts

        self.__write_table = copy.deepcopy(self.__init_write_table)
        width = self.__width
        height = self.__height

        romultic_data = []

        while True:
            max_pattern = {"score": -1.0, "rows": list(), "cols": [0 for x in range(width)], "conf": list()}

            # analyze unfixed PEs
            unfixed_PEs = [(x,y) for x in range(width) for y in range(height)\
                                if not self.__isFixed((x,y))]

            if len(unfixed_PEs) == 0:
                break
            # enumerate conf pattern
            target_confs = []
            for (x,y) in unfixed_PEs:
                for operand_pattern in operand_pattern_list:
                    if any([field in self.__conf_data[x][y] for field in operand_pattern]):
                        conf = {field: self.__conf_data[x][y][field] if field in self.__conf_data[x][y] else 0\
                                 for field in operand_pattern}
                        if not conf in target_confs:
                            target_confs.append(conf)

            # 各パターンでビット数を計算
            for conf in target_confs:
                # 真理値表の生成
                # bits log2(width) + log2(height)
                tt = exprvars('x', self.__col_bitwidth + self.__row_bitwidth)

                # 書き込み済みなら0, 同一コンフィギュレーションなら1, それ以外はDont care
                func_s = ""
                for x in range(width):
                    for y in range(height):
                        if not self.__writable((x,y), conf):
                            func_s += "0" # False
                        elif self.__effective_bits((x,y), conf) != 0:
                            func_s += "1" # True
                        else:
                            func_s += "-" # Dont care
                    for y in range(width, 2**self.__row_bitwidth):
                        func_s += "-"

                # Dont careで穴埋め
                for i in range(2 ** (self.__col_bitwidth + self.__row_bitwidth) - width * height):
                    func_s += "-" # Dont care

                # 論理関数の生成と圧縮
                func = truthtable(tt, func_s)
                func_min = espresso_tts(func)

                max_score = 0
                max_idx = -1

                if len(func_min) == 1:
                    ret = self.__decode_espresso_results(func_min[0])

                    for i in range(len(ret)):
                        score = 0
                        rows, cols = ret[i]
                        for x in range(width):
                            for y in range(height):
                                if rows[y] == 1 and cols[x] == 1:
                                    score += self.__effective_bits((x,y), conf)
                        if score > max_score:
                            max_idx = i
                            max_score = score

                else:
                    raise RuntimeError(["Fatal error while compressing by espresso"])

                if max_score > 0:
                    if max_score > max_pattern["score"]:
                        max_pattern["score"] = max_score
                        max_pattern["rows"] , max_pattern["cols"] = ret[max_idx]
                        max_pattern["conf"] = conf

            # update
            for x in range(width):
                if max_pattern["cols"][x] == 1:
                    for y in range(height):
                        if max_pattern["rows"][y] == 1:
                            self.__update((x,y), max_pattern["conf"])

            romultic_data.append(max_pattern)

        return romultic_data

    def __decode_espresso_results(self, result):
        if str(result) != "0":
            # separates results by OR condition
            if result.ASTOP == "or":
                result_or = result.xs
            else:
                result_or = list()
                result_or.append(result)

            ret = list()

            for i in range(len(result_or)):
                rows = [1 for i in range(self.__height)]
                cols = [1 for i in range(self.__width)]
                if result_or[i].ASTOP == "lit":
                    num_search = re.search("[0-9]+", str(result_or[i]))
                    num = int(num_search.group())
                    if re.match("~x\[[0-9]+\]", str(result_or[i])):
                        # negative
                        if num >= self.__row_bitwidth:
                            # col
                            for x in range(self.__width):
                                if x & (1 << (num - self.__row_bitwidth)) != 0:
                                    cols[x] = 0
                        else:
                            # row
                            for y in range(self.__height):
                                if y & (1 << num) != 0:
                                    rows[y] = 0
                    else:
                        # positive
                        if num >= self.__row_bitwidth:
                            # col
                            for x in range(self.__width):
                                if x & (1 << (num - self.__row_bitwidth)) == 0:
                                    cols[x] = 0
                        else:
                            # row
                            for y in range(self.__height):
                                if y & (1 << num) == 0:
                                    rows[y] = 0

                elif result_or[i].ASTOP == "and":
                    for ele in result_or[i].xs:
                        if ele.ASTOP == "lit":
                            num_search = re.search("[0-9]+", str(ele))
                            num = int(num_search.group())
                            if re.match("~x\[[0-9]+\]", str(ele)):
                                # negative
                                if num >= self.__row_bitwidth:
                                    # col
                                    for x in range(self.__width):
                                        if x & (1 << (num - self.__row_bitwidth)) != 0:
                                            cols[x] = 0
                                else:
                                    # row
                                    for y in range(self.__height):
                                        if y & (1 << num) != 0:
                                            rows[y] = 0
                            else:
                                # positive
                                if num  >= self.__row_bitwidth:
                                    # col
                                    for x in range(self.__width):
                                        if x & (1 << (num - self.__row_bitwidth)) == 0:
                                            cols[x] = 0
                                else:
                                    # row
                                    for y in range(self.__height):
                                        if y & (1 << num) == 0:
                                            rows[y] = 0
                ret.append((rows, cols))
        else:
            ret = [([0 for i in range(self.__height)], [0 for i in range(self.__width)])]

        return ret
