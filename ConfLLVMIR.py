#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

import llvmlite.ir as ll
import llvmlite.binding as llvm

# element type
i32 = ll.IntType(32)
i8 = ll.IntType(8)

class ConfLLVMIR(object):
    """Utility for exporting conf data in LLVM"""

    def __init__(self):
        llvm.initialize()
        llvm.create_target_data("E-m:m-p:32:32-i8:8:32-i16:16:32-i64:64-n32-S64")
        target = llvm.Target("mips-mcpu=mips32")
        self.__module = ll.Module()


    def add_variable(self, name, data):
        """Add one data as a grobal variable in LLVM IR.
            Args:
                name(str): variable name
                data(int or str): data to be stored
            Raise:
                If unsupported data type is specified, it raises TypeError.
        """
        if type(data) is int:
            store_data = ll.GlobalVariable(self.__module, i32, name)
            store_data.initializer = ll.Constant(i32, data)
            store_data.align = 4
        elif type(data) is str:
            data += "\0"
            store_data = ll.GlobalVariable(self.__module, ll.ArrayType(i8, len(data)), name)
            store_data.initializer = ll.Constant(ll.ArrayType(i8, len(data)), bytearray(data.encode()))
            store_data.align = 16
        else:
            raise TypeError("Unsupported data type")


    def add_array(self, name, data):
        """Add an array as a grobal variable in LLVM IR.
            Args:
                name(str): variable name
                data(list-like of int): array to be stored
            Raise:
                If unsupported data type is specified, it raises TypeError.
                If empty list is specified, it raises IndexError.
        """
        if len(data) > 0:
            if type(data[0]) is int:
                store_data = ll.GlobalVariable(self.__module, ll.ArrayType(i32, len(data)), name)
                store_data.initializer = ll.Constant.literal_array([ll.Constant(i32, d) for d in data])
                store_data.align = 64
            else:
                raise TypeError("Unsupported data type")
        else:
            raise IndexError("Data is empty")

    def add_metadata(self, name, data):
        """Add a metadata in LLVM IR.

            Args:
                name(str): metadata name
                data(str): metadata to be included
        """
        metadata = ll.MetaDataString(self.__module, str(data))
        self.__module.add_metadata((metadata, name))

    def get_IR(self):
        """Get the LLVM IR codes.

            Args: None

            Returns:
                str: LLVM IR code
        """
        llvm_ir = str(self.__module)
        parsed_ir = str(llvm.parse_assembly(llvm_ir))
        for metadata in self.__module.metadata:
            parsed_ir += str(metadata) + "\n"
        return parsed_ir
