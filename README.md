# About GenMap
GenMap is an application mapping framework for spatially mapping CGRAs implemented with Python.
It uses a multi-objective genetic algorithm.
Therefore, it is easy to add your own objectives to be optimized.
It also contains a leakage power optimization method, a dynamic power estimation model, and RoMultiC configuration generation.

## Publications
1. Takuya Kojima, Nguyen Anh Vu Doan, Hideharu Amano, “GenMap: A Genetic Algorithmic Approach for Optimizing Spatial Mapping of Coarse Grained Reconfigurable Architectures”, IEEE Transactions on Very Large Scale Integration Systems (VLSI), Vol. 28, no. 11, pp.2383-2396, Nov 2020. [[IEEE Xplore]](https://ieeexplore.ieee.org/document/9149647)
1. Takeharu Ikezoe, Takuya Kojima and Hideharu Amano, “A Coarse-Grained Reconfigurable Architecture with a Fault Tolerant Non-Volatile Configurable Memory,” 2019 International Conference on Field-Programmable Technology (ICFPT), Tianjin, China, 2019, pp. 81-89. [[IEEE Xplore]](https://ieeexplore.ieee.org/abstract/document/8977850)
1. Takuya Kojima and Hideharu Amano, “A Configuration Data Multicasting Method for Coarse-Grained Reconfigurable Architectures”, 28th International Conference on Field Programmable Logic and Applications (FPL), Dublin, Ireland, August, 2018. [[IEEE Xplore]](https://ieeexplore.ieee.org/abstract/document/8533501)
1. Takuya Kojima, Naoki Ando, Hayate Okuhara, Hideharu Amano, “Glitch-aware Variable Pipeline Optimization for CGRAs”, ReConFig 2017, Mexico, December 2017. [[IEEE Xplore]](https://ieeexplore.ieee.org/document/8279797)
1. Takuya Kojima, Naoki Ando, Hayate Okuhara, Ng. Anh Vu Doan, Hideharu Amano, “Body Bias Optimization for Variable Pipelined CGRA”, 27th International Conference on Field-Programmable Logic and Applications(FPL), Belgium, September 2017. [[IEEE Xplore]](https://ieeexplore.ieee.org/document/8056851)

## Installation
Please see [Installation guide](./docs/installation_guide.md)

## Included architecture definitions
GenMap supports following CGRA architectures by default:
1. CMA-SOTB2 [[K.Masuyama, *et al*]](https://ieeexplore.ieee.org/abstract/document/7393280) (a.k.a. NVCMA [[T.Ikezoe, *et al*]](https://ieeexplore.ieee.org/abstract/document/8641712) )
1. CC-SOTB [[Y.Matsushita, *et al*]](https://ieeexplore.ieee.org/abstract/document/7577346) 
1. CC-SOTB2 (VPCMA) [[N.Ando, *et al*]](https://ieeexplore.ieee.org/abstract/document/7929537) 
1. VPCMA2 [[T.Kojima, *et al*]](https://ieeexplore.ieee.org/abstract/document/9034924) 
1. RHP-CGRA [[A.Podobas, *et al*]](https://ieeexplore.ieee.org/abstract/document/9153262)

Architecture information and parameters for some simulation are in the [chip_files](./chip_files)

## Quick Tutorial
This tutorial introduces you to GenMap overview.

### Run GenMap
At first, make a working directory. In this tutorial, the working directory is in the same directory as the GenMap.
```
(GenMap_env) # mkdir work
(GenMap_env) # cd work
```

Please copy a sample application DFG file to a working directory (*gray* in this example).
```
(GenMap_env) # cp ../GenMap/app_samples/gray.dot ./
```

Please copy architecture definition file and simulation paramter file to working direcotry (*CCSOTB2* in this example).
```
(GenMap_env) # cp ../GenMap/chip_files/CCSOTB2/arch.xml ./
(GenMap_env) # cp ../GenMap/chip_files/CCSOTB2/simdata.xml ./
```

Please copy optimization setting to working directory.
```
(GenMap_env) # cp ../GenMap/OptimizationParameters.xml ./
```

To run GenMap, please execute:
```
(GenMap_env) # python3 ../GenMap/GenMap.py gray.dot 10 [--nproc num]
```
At least, you have to specify two positional arguments. The first is an application DFG file, and the second is operation frequency (default MHz).
For other optional arguments, please see help (``python GenMap.py -h``)
You can specify the process count for multiprocessing (default 1).

After GenMap starts, optimization status will appear like below.
```
Generation 121:  40%|█▌  | 120/300 [1:20:02<2:07:56, 42.65s/it, hof_len=97, stall=6]
Wire_Length: , max=29, min=27                                                       
Mapping_Width: , max=3, min=2                                                       
Op_Mapping_Width: , max=3, min=2                                                    
Power_Consumption: , max=0.589, min=0.347                                           
Time_Slack: , max=61.2, min=0.462    
```

## Stop optimization before reaching termination condition
The genetic algorithm will stop evolution when satisfying either of the following conditions:
1. reaching the maximum generation (``Maximum generation``)
1. no improvement during a specified generation (``Maximum stall``)

These parameters are configured in the setting file ``OptimizationParameters.xml``.

If you want to exit the optimization before satisfying the above condition,
send ``USR1`` signal to the main process as follows.

```
$ kill -USR1 {PID of GenMap}
```

PID will be shown in lauch message.

## Generate Configuration
If the above optimization finishes successfully, it will save a result *gray.dump* (in default).
By loading this result, you can generate configuration data for the architecture.

Please execute:
```
(GenMap_env) # python3 ../GenMap/CCSOTB2_ConfGen.py gray.dump
```

Then a shell will starts.
```
=== GenMap solution selection utility ===
GenMap shell>   
```

To show all solutions, execute:
```
GenMap shell> show
+-----+-------------+---------------+------------------+--------------------+---------------------+
|  ID | Wire_Length | Mapping_Width | Op_Mapping_Width | Power_Consumption  |      Time_Slack     |
+-----+-------------+---------------+------------------+--------------------+---------------------+
|  0  |     26.0    |      3.0      |       3.0        | 2.375386336518864  | 0.25644671033332855 |
|  1  |     26.0    |      3.0      |       3.0        | 2.4910062914105766 |  2.4540015123333276 |
...
...
| 157 |     37.0    |      7.0      |       7.0        | 1.029479529863405  |  1.0105863153333274 |
| 158 |     37.0    |      7.0      |       7.0        | 1.0658122223530275 |  1.5835502433333275 |
+-----+-------------+---------------+------------------+--------------------+---------------------+

```

To select a solution, execute:
```
GenMap shell> select 0 # to specify the ID number
```

To save configuration, execute:
```
GenMap shell>  save
```

In the GenMap Shell, the following commands are available.
1. show: show the result
1. sort: sort the solutions by specified objective
1. filter: filter the solutions with some conditions
1. select: select a solution
1. reset: reset the filtering and selection
1. view: view mapping of the selected solution
1. save: save configurations of the selected solution
1. quit: quit the shell

You can see the usage of these command in GenMap Shell with ``--help`` option as follows.

```
GenMap shell> save --help
usage: save [options...]
It generates configuration files of selected solutions

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        specify output directory name
  -f, --force           overwrite without prompt
  -p PREFIX, --prefix PREFIX
                        specify prefix of output file names (default:
                        app_name)
  -s STYLE [STYLE ...], --style STYLE [STYLE ...]
                        Pass the space separated arguments to configuration
                        generator
```


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
Also, some environment variables like GRB_LICENSE_FILE are needed for gurobi itself.

Please see [the official web site](https://www.gurobi.com/documentation/9.1/quickstart_mac/setting_environment_variab.html)

### For Mosek
```
$ export GMP_ILP_SOLVER=mosek
```

# Write an Application 
For GenMap, the application DFG file is described in *DOT* format.
For more information, please refer to [To Be Added]()

# How to customize 
You can customize the following:
1. Architectures
    1. PE Size
    1. PE Array Topology  
    etc.
1. Optimization objectives
1. Routing algorithm

For more information, please refer to [To Be Added]()
