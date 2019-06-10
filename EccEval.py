from EvalBase import EvalBase
from FaultArchModel import FaultArchModel, CMASOTB2_PE_CONF_PARAM


class SeedMap(object):
    def __init__(self):
        import multiprocessing
        self.vals = []
        self.countTouching = multiprocessing.Value('i', 0)

    def gen(self, num):
        import multiprocessing
        if len(self.vals) != 0:
            return
        for i in range(num):
            self.vals.append(multiprocessing.Value('i', 0))

    def touch(self, i):
        with self.countTouching.get_lock() and self.vals[i].get_lock():
            if self.vals[i].value != 0:
                return
            self.countTouching.value += 1
            self.vals[i].value = 1
            # print("Find Vaild Mapping(PE seed[", i, "])")
            if self.countTouching.value == len(self.vals):
                # print("FIND AVAIL MAP LENGTH:", self.countTouching.value)
                raise RuntimeError("this app is available with each seed!!!")

    def isTouched(self, i):
        return self.vals[i].value == 1

    @property
    def count(self):
        return self.countTouching.value


class EccEval(EvalBase):
    seed_map = None

    def __init__(self):
        pass

    @staticmethod
    def eval(CGRA, app, sim_params, individual):

        import os

        PEs_conf = EccEval._get_PEs_conf(CGRA, app, individual)

        env_ecc = bool(int(os.getenv('GENMAP_ECC', '1')))
        env_stack_rate = float(os.getenv('GENMAP_STACK_RATE', '0.02'))
        env_random_seed_start = int(os.getenv('GENMAP_RANDOM_SEED_START', '0'))
        env_random_seed_num = int(os.getenv('GENMAP_RANDOM_SEED_NUM', '1000'))

        faultArchModel_width = 8
        faultArchModel_height = 8

        for seed in range(env_random_seed_start,
                          env_random_seed_start + env_random_seed_num):
            if not EccEval.seed_map.isTouched(seed):
                faultArchModel = FaultArchModel(
                    num_pes=faultArchModel_width * faultArchModel_height,
                    stack0_rate=env_stack_rate / 2,
                    stack1_rate=env_stack_rate / 2,
                    ecc=env_ecc,
                    seed=seed)

                for i in range(faultArchModel_width):
                    for j in range(faultArchModel_height):
                        PE_conf = PEs_conf[i][j]

                        for conf_keys in CMASOTB2_PE_CONF_PARAM:
                            if not conf_keys['name'] in PE_conf:
                                PE_conf[conf_keys['name']] = None

                        PE_id = i + j * faultArchModel_height
                        if not faultArchModel.checkPeAvailablity(
                                PE_id, PE_conf):
                            break
                    else:
                        continue
                    break
                else:
                    # みつけた
                    EccEval.seed_map.touch(seed)

        return 1

    @staticmethod
    def _get_PEs_conf(CGRA, app, individual):
        width, height = CGRA.getSize()

        comp_dfg = app.getCompSubGraph()

        routed_graph = individual.routed_graph

        confs = [[{} for y in range(height)] for x in range(width)]

        # ALUs
        for op_label, (x, y) in individual.mapping.items():
            opcode = comp_dfg.node[op_label]["op"]
            confs[x][y]["OPCODE"] = CGRA.getOpConfValue((x, y), opcode)
            alu = CGRA.get_PE_resources((x, y))["ALU"]
            pre_nodes = list(routed_graph.predecessors(alu))
            operands = {
                routed_graph.edges[(v, alu)]["operand"]: v
                for v in pre_nodes if "operand" in routed_graph.edges[(v, alu)]
            }

            if "left" in operands and "right" in operands:
                confs[x][y]["SEL_A"] = CGRA.getNetConfValue(
                    alu, operands["left"])
                confs[x][y]["SEL_B"] = CGRA.getNetConfValue(
                    alu, operands["right"])
            elif "left" in operands:
                confs[x][y]["SEL_A"] = CGRA.getNetConfValue(
                    alu, operands["left"])
                pre_nodes.remove(operands["left"])
                if len(pre_nodes) > 0:
                    confs[x][y]["SEL_B"] = CGRA.getNetConfValue(
                        alu, pre_nodes[0])
            elif "right" in operands:
                confs[x][y]["SEL_B"] = CGRA.getNetConfValue(
                    alu, operands["right"])
                pre_nodes.remove(operands["right"])
                if len(pre_nodes) > 0:
                    confs[x][y]["SEL_A"] = CGRA.getNetConfValue(
                        alu, pre_nodes[0])
            else:
                confs[x][y]["SEL_A"] = CGRA.getNetConfValue(alu, pre_nodes[0])
                if len(pre_nodes) > 1:
                    confs[x][y]["SEL_B"] = CGRA.getNetConfValue(
                        alu, pre_nodes[1])

        # SEs
        for x in range(width):
            for y in range(height):
                se_list = CGRA.get_PE_resources((x, y))["SE"]
                if len(se_list) == 2:
                    # for each SE
                    for se_id, se_sublist in se_list.items():
                        for se in se_sublist:
                            if se in routed_graph.nodes():
                                pre_node = list(
                                    routed_graph.predecessors(se))[0]
                                confs[x][y][CGRA.getWireName(
                                    se)] = CGRA.getNetConfValue(se, pre_node)
                else:
                    raise TypeError("CMA-SOTB2 assumes two SEs per PE")

        return confs

    @staticmethod
    def isMinimize():
        return False

    @staticmethod
    def name():
        return "Mapping_Width"