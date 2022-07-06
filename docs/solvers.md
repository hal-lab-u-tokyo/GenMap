# How to change ILP solvers
Some optimization in GenMap is handled as Integer Linear Program (ILP),
and you can change ILP solvers as you like.

The current version supports the following solvers.
1. CBC (default)
1. Gurobi (installation and license are needed)
1. Mosek (installation and license are needed)

To specify the solver to be used,
you can set the environment variable as below.
### For CBC
```
$ export GMP_ILP_SOLVER=cbc
```

### For Gurobi
```
$ export GMP_ILP_SOLVER=gurobi
```
Also, some environment variables like GRB_LICENSE_FILE are needed for Gurobi itself.

Please see [the official web site](https://www.gurobi.com/documentation/9.1/quickstart_mac/setting_environment_variab.html)

### For Mosek
```
$ export GMP_ILP_SOLVER=mosek
```
