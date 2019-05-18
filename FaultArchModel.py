from enum import Enum

CMASOTB2_PE_CONF_PARAM = [
    {
        'name': 'OPCODE',
        'width': '4'
    }, {
        'name': 'SEL_A',
        'width': '3'
    }, {
        'name': 'SEL_B',
        'width': '3'
    }, {
        'name': 'OUT_A_NORTH',
        'width': '3'
    }, {
        'name': 'OUT_A_SOUTH',
        'width': '2'
    }, {
        'name': 'OUT_A_EAST',
        'width': '3'
    }, {
        'name': 'OUT_A_WEST',
        'width': '2'
    }, {
        'name': 'OUT_B_NORTH',
        'width': '4'
    }, {
        'name': 'OUT_B_EAST',
        'width': '3'
    }, {
        'name': 'OUT_B_WEST',
        'width': '3'
    }
]

class BitState(object):
    Good = 0
    Stack0 = 1
    Stack1 = 2

class FaultArchModel(object):
    def __init__(self, num_pes=64, stack0_rate=0.0, stack1_rate=0.0, seed=None, ecc=True):
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
            self._checkEccPeAvailablity(PE_id, PE_conf)
        else:
            self._checkNonEccPeAvailablity(PE_id, PE_conf)
        
    def _checkEccPeAvailablity(self, PE_id, PE_conf):
        pe_model = self.model[PE_id]
        print("run when ecc is disabled.")

    def _checkNonEccPeAvailablity(self, PE_id, PE_conf):
        pe_model = self.model[PE_id]
        print("run when ecc is enabled.")
    # def check(pe_id, conf_data):
    #     pe_model = self.model[pe_id]
    #     pe_model.m