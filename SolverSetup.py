#  This file is part of GenMap and released under the MIT License, see LICENSE.
#  Author: Takuya Kojima

import os

import pulp
import cvxpy as cp

try:
    import mosek as MOSEK
except ImportError:
    MOSEK = None

class SolverSetup():
    class SolverSetupError(Exception):
        pass
    def __init__(self, sol_type, threads = 1):
        self.__sol_type_list = ["ILP", "CP"]
        self.__threads = threads
        self.__ilp_solver_setup = {"gurobi": self.__gurobi_ilp_setup,
                                   "mosek":  self.__mosek_ilp_setup,
                                   "cbc":    self.__cbc_ilp_setup}
        self.__cp_solver_setup = {"ecos": self.__ecos_cp_setup,
                                  "scs": self.__scs_cp_setup,
                                  "mosek":  self.__mosek_cp_setup}

        if not sol_type in self.__sol_type_list:
            raise ValueError("sol_type must be in " +\
                             str(self.__sol_type_list))
        self.__solver = None
        if sol_type == "ILP":
            # Integer Linear Program
            self.__setup_ilp()
        elif sol_type == "CP":
            # Convex Optimization Program
            self.__setup_cp()

    def getSolver(self):
        return self.__solver


    def __mosek_lic_check(self):
        prob = pulp.LpProblem("test", pulp.LpMinimize)
        x = pulp.LpVariable("x", 0, 1, pulp.LpContinuous)
        prob += x
        prob += x <= 1
        try:
            prob.solve(self.__solver)
        except MOSEK.Error as e:
            print(e)
            return False

        return True

    def __setup_cp(self):
        # supported solvers: ecos, scs, mosek
        solver = os.getenv("GMP_CP_SOLVER")
        if solver is None:
            solver = "ecos"
        if not solver.lower() in self.__cp_solver_setup.keys():
            print("WARN: CP solver specified by the GMP_CP_SOLVER:",
                    solver, "is not supported. The default solver (ecos) is used")
            solver = "ecos"
        self.__cp_solver_setup[solver.lower()]()

    def __setup_ilp(self):
        # supported solvers: cbc, gurobi, mosek
        solver = os.getenv("GMP_ILP_SOLVER")
        if solver is None:
            # default
            solver = "cbc"
        if not solver.lower() in self.__ilp_solver_setup.keys():
            print("WARN: ILP solver specified by the GMP_ILP_SOLVER:",
                    solver, "is not supported. The default solver (cbc) is used")
            solver = "cbc"
        self.__ilp_solver_setup[solver.lower()]()

    def __gurobi_ilp_setup(self):

        self.__solver = pulp.GUROBI_CMD(msg = False, \
                                        threads = self.__threads)
        if not self.__solver.available():
            raise SolverSetup.SolverSetupError\
                ("Gurobi is not available. Please check PATH setting and" +
                 " make sure gurobi is installed and you have a valid license")


    def __mosek_ilp_setup(self):
        # check installation
        if MOSEK is None:
            raise SolverSetup.SolverSetupError("mosek is not installed. " + \
                "Please install mosek's python API like 'pip install mosek'")
        # check multithread option
        options = {MOSEK.iparam.num_threads: self.__threads,
                     MOSEK.iparam.intpnt_multi_thread: \
                                    MOSEK.onoffkey.off,\
                    MOSEK.dparam.mio_max_time: 3600.0}

        self.__solver = pulp.MOSEK(msg=False, options = options)
        if not self.__solver.available():
            raise SolverSetup.SolverSetupError("Unexpected error: fails to setup mosek")
        # check license
        if not self.__mosek_lic_check():
            raise SolverSetup.SolverSetupError("Please check your license for mosek")

    def __cbc_ilp_setup(self):
        self.__solver = pulp.PULP_CBC_CMD(msg = False,\
                                         threads = self.__threads)

    def __ecos_cp_setup(self):
        if not "ECOS" in cp.installed_solvers():
            raise SolverSetup.SolverSetupError\
                ("ECOS is not installed.")

        print("WARN: ECOS might be fail to solve a convex problem for a certain condition")
        self.__solver = {"solver": "ECOS", "verbose": False}

    def __scs_cp_setup(self):
        if not "SCS" in cp.installed_solvers():
            raise SolverSetup.SolverSetupError\
                ("SCS is not installed.")
        print("WARN: SCS might be fail to solve a convex problem for a certain condition")
        self.__solver = {"solver": "SCS", "verbose": False}

    def __mosek_cp_setup(self):
        if not "MOSEK" in cp.installed_solvers() or MOSEK is None:
            raise SolverSetup.SolverSetupError\
                ("mosek is not installed. " + "Please install mosek's python API like 'pip install mosek'")
        solver = {"solver": "MOSEK", "verbose": False}

        mt_flag = MOSEK.onoffkey.on if self.__threads > 1 else \
                    MOSEK.onoffkey.off

        solver["mosek_params"] = {MOSEK.iparam.num_threads: self.__threads,
                                  MOSEK.iparam.intpnt_multi_thread: mt_flag }

        # check license
        self.__solver = pulp.MOSEK(msg=False)
        if not self.__mosek_lic_check():
            self.__solver = None
            raise SolverSetup.SolverSetupError("Please check your license for mosek")

        self.__solver = solver
