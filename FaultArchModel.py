from enum import Enum

CMASOTB2_PE_CONF_PARAM = [
    {
        'name': 'OPCODE',
        'width': 4
    }, {
        'name': 'SEL_A',
        'width': 3
    }, {
        'name': 'SEL_B',
        'width': 3
    }, {
        'name': 'OUT_A_NORTH',
        'width': 3
    }, {
        'name': 'OUT_A_SOUTH',
        'width': 2
    }, {
        'name': 'OUT_A_EAST',
        'width': 3
    }, {
        'name': 'OUT_A_WEST',
        'width': 2
    }, {
        'name': 'OUT_B_NORTH',
        'width': 4
    }, {
        'name': 'OUT_B_EAST',
        'width': 3
    }, {
        'name': 'OUT_B_WEST',
        'width': 3
    }
]

CORRECTABLE_DISTANCE = 3

class BitState(object):
    Good = 0
    Stack0 = 1
    Stack1 = 2

class FaultArchModel(object):
    def __init__(self, num_pes=64, stack0_rate=0.0, stack1_rate=0.0, seed=0, ecc=True):
        import os
        self._stack0_rate = stack0_rate
        self._stack1_rate = stack1_rate
        self._seed = seed
        self._num_pes = num_pes
        self._ecc = ecc
        self.model = None
        self._generateFaultModel()
    
    def _flat_for(self, a, f):
        a = a.reshape(-1)
        for i, v in enumerate(a):
            a[i] = f(v)
    
    def _func_assign_bit_state(self, x):
        if x < self._stack0_rate:
            return BitState.Stack0
        elif x < self._stack0_rate + self._stack1_rate:
            return BitState.Stack1
        else:
            return BitState.Good
        
    def _generateFaultModel(self):
        import numpy as np

        np.random.seed(self._seed)
        if self._ecc:
            self.model = np.random.rand(self._num_pes, 3, 23)
        else:
            self.model = np.random.rand(self._num_pes, 30)
        self._flat_for(self.model, self._func_assign_bit_state)

    def checkPeAvailablity(self, PE_id, PE_conf):
        if self.model is None:
            raise RuntimeError("FaultArchModel.model is None!")
        
        if self._ecc:
            return self._checkEccPeAvailablity(PE_id, PE_conf)
        else:
            return self._checkNonEccPeAvailablity(PE_id, PE_conf)
        
    def _checkEccPeAvailablity(self, PE_id, PE_conf):
        pe_model = self.model[PE_id]
        write_data = self._pack_raw_data_for_ecc(PE_conf)

        if not self.__is_all_none(write_data[0]):
            possible_write_data0 = self._gen_possible_write_data([write_data[0]])
            if not self.is_correctable_distance(pe_model[0], possible_write_data0):
                return False

        if not self.__is_all_none(write_data[1]):
            possible_write_data1 = self._gen_possible_write_data([write_data[1]])
            if not self.is_correctable_distance(pe_model[1], possible_write_data1):
                return False

        if not self.__is_all_none(write_data[2]):
            possible_write_data2 = self._gen_possible_write_data([write_data[2]])
            if not self.is_correctable_distance(pe_model[2], possible_write_data2):
                return False

        return True

    def is_correctable_distance(self, model, possible_write_data_array):
        for possible_write_data in possible_write_data_array:
            encoded_possible_write_data = self._encode_ecc(possible_write_data)
            distance = self._calc_distance(model=model, write_data=encoded_possible_write_data)
            if distance <= CORRECTABLE_DISTANCE:
                # if distance == 0:
                return True
        return False
    
    def __is_all_none(self, write_data):
        for element in write_data:
            if not element is None:
                return False
        return True
    
    def _gen_possible_write_data(self, write_data_words):
        import copy
        new_write_data_words = copy.deepcopy(write_data_words)
        for i, write_data_word in enumerate(new_write_data_words):
            for j, element in enumerate(write_data_word):
                if element is None:
                    new_write_data_words[i][j] = 0
                    new_word = copy.deepcopy(write_data_word)
                    new_word[j] = 1
                    new_write_data_words.append(new_word)
        return new_write_data_words

    def _pack_raw_data_for_ecc(self, PE_conf):
        import numpy as np
        result_list = [[],[],[]]
        result_list[0].extend(self.__expand_bin('OPCODE', PE_conf['OPCODE']))
        result_list[0].extend(self.__expand_bin('SEL_A', PE_conf['SEL_A']))
        result_list[0].extend(self.__expand_bin('SEL_B', PE_conf['SEL_B']))
        result_list[1].extend(self.__expand_bin('OUT_A_NORTH', PE_conf['OUT_A_NORTH']))
        result_list[1].extend(self.__expand_bin('OUT_A_SOUTH', PE_conf['OUT_A_SOUTH']))
        result_list[1].extend(self.__expand_bin('OUT_A_EAST', PE_conf['OUT_A_EAST']))
        result_list[1].extend(self.__expand_bin('OUT_A_WEST', PE_conf['OUT_A_WEST']))
        result_list[2].extend(self.__expand_bin('OUT_B_NORTH', PE_conf['OUT_B_NORTH']))
        result_list[2].extend(self.__expand_bin('OUT_B_EAST', PE_conf['OUT_B_EAST']))
        result_list[2].extend(self.__expand_bin('OUT_B_WEST', PE_conf['OUT_B_WEST']))

        for ecc_unit in result_list:
            ecc_unit_len = len(ecc_unit)
            for i in range(12 - ecc_unit_len):
                ecc_unit.append(None)

        return result_list

    def __expand_bin(self, conf_name, conf_val):
        name = None
        width = None
        for param in CMASOTB2_PE_CONF_PARAM:
            if param['name'] == conf_name:
                name = conf_name
                width = param['width']
        
        if name is None:
            raise RuntimeError('Cannot find name \'%d\'' % conf_name)

        result_list = []

        for i in range(width - 1, -1, -1):
            if not conf_val is None:
                result_list.append((conf_val >> i) & 1)
            else:
                result_list.append(None)

        return result_list

    def _checkNonEccPeAvailablity(self, PE_id, PE_conf):
        pe_model = self.model[PE_id]
        write_data = self._pack_raw_data_for_non_ecc(PE_conf)
        distance = self._calc_distance(model=pe_model, write_data=write_data)

        return distance == 0

    def _calc_distance(self, model, write_data):
        distance = 0
        if not len(model) == len(write_data):
            raise RuntimeError("model length doesnt match write_data")

        for element in zip(model, write_data):
            element_model = element[0]
            element_write_data = element[1]

            if element_model == BitState.Stack0 and element_write_data == 1:
                distance += 1
            elif element_model == BitState.Stack1 and element_write_data == 0:
                distance += 1

        return distance

    def _pack_raw_data_for_non_ecc(self, PE_conf):
        import numpy as np
        result_list = []
        result_list.extend(self.__expand_bin('OPCODE', PE_conf['OPCODE']))
        result_list.extend(self.__expand_bin('SEL_A', PE_conf['SEL_A']))
        result_list.extend(self.__expand_bin('SEL_B', PE_conf['SEL_B']))
        result_list.extend(self.__expand_bin('OUT_A_NORTH', PE_conf['OUT_A_NORTH']))
        result_list.extend(self.__expand_bin('OUT_A_SOUTH', PE_conf['OUT_A_SOUTH']))
        result_list.extend(self.__expand_bin('OUT_A_EAST', PE_conf['OUT_A_EAST']))
        result_list.extend(self.__expand_bin('OUT_A_WEST', PE_conf['OUT_A_WEST']))
        result_list.extend(self.__expand_bin('OUT_B_NORTH', PE_conf['OUT_B_NORTH']))
        result_list.extend(self.__expand_bin('OUT_B_EAST', PE_conf['OUT_B_EAST']))
        result_list.extend(self.__expand_bin('OUT_B_WEST', PE_conf['OUT_B_WEST']))
        return result_list

    """
    12bitに11bitを付加して23bitに符号化する
    """
    def _encode_ecc(self, list_data):
        import copy
        newlist = copy.deepcopy(list_data)
        newlist.extend([
            list_data[0]^list_data[1]^list_data[2]^list_data[6]^list_data[7]^list_data[8]^list_data[11],
            list_data[0]^list_data[3]^list_data[4]^list_data[6]^list_data[7]^list_data[9]^list_data[11],
            list_data[1]^list_data[3]^list_data[5]^list_data[6]^list_data[8]^list_data[9]^list_data[11],
            list_data[2]^list_data[4]^list_data[5]^list_data[7]^list_data[8]^list_data[9]^list_data[11],
            list_data[2]^list_data[3]^list_data[5]^list_data[6]^list_data[7]^list_data[10]^list_data[11],
            list_data[0]^list_data[4]^list_data[5]^list_data[6]^list_data[8]^list_data[10]^list_data[11],
            list_data[1]^list_data[3]^list_data[4]^list_data[7]^list_data[8]^list_data[10]^list_data[11],
            list_data[1]^list_data[2]^list_data[4]^list_data[6]^list_data[9]^list_data[10]^list_data[11],
            list_data[0]^list_data[1]^list_data[5]^list_data[7]^list_data[9]^list_data[10]^list_data[11],
            list_data[0]^list_data[2]^list_data[3]^list_data[8]^list_data[9]^list_data[10]^list_data[11],
            list_data[0]^list_data[1]^list_data[2]^list_data[3]^list_data[4]^list_data[5]^list_data[6]^list_data[7]^list_data[8]^list_data[9]^list_data[10]
        ])
        return newlist

