# About GenMap
GenMap is an application mapping framework for spatially mapping CGRAs implemented with Python.
It uses a multi-objective genetic algorithm.
Therefore, it is easy to add your own objectives to be optimized.
It also contains a leakage power optimization method, a dynamic power estimation model, and RoMultiC configuration generation.

## Publications
1. Takuya Kojima, Hayate Okuhara, Masaaki Kondo, Hideharu Amano, "Body Bias Control on a CGRA based on Convex Optimization", COOLCHIPS25, Japan, April, 2022.  [[IEEE Xplore]](https://ieeexplore.ieee.org/document/9772708)
1. Takuya Kojima, Nguyen Anh Vu Doan, Hideharu Amano, "GenMap: A Genetic Algorithmic Approach for Optimizing Spatial Mapping of Coarse Grained Reconfigurable Architectures", IEEE Transactions on Very Large Scale Integration Systems (VLSI), Vol. 28, no. 11, pp.2383-2396, Nov 2020. [[IEEE Xplore]](https://ieeexplore.ieee.org/document/9149647)
1. Takeharu Ikezoe, Takuya Kojima and Hideharu Amano, "A Coarse-Grained Reconfigurable Architecture with a Fault Tolerant Non-Volatile Configurable Memory," 2019 International Conference on Field-Programmable Technology (ICFPT), Tianjin, China, 2019, pp. 81-89. [[IEEE Xplore]](https://ieeexplore.ieee.org/abstract/document/8977850)
1. Takuya Kojima and Hideharu Amano, "A Configuration Data Multicasting Method for Coarse-Grained Reconfigurable Architectures", 28th International Conference on Field Programmable Logic and Applications (FPL), Dublin, Ireland, August, 2018. [[IEEE Xplore]](https://ieeexplore.ieee.org/abstract/document/8533501)
1. Takuya Kojima, Naoki Ando, Hayate Okuhara, Hideharu Amano, "Glitch-aware Variable Pipeline Optimization for CGRAs", ReConFig 2017, Mexico, December 2017. [[IEEE Xplore]](https://ieeexplore.ieee.org/document/8279797)
1. Takuya Kojima, Naoki Ando, Hayate Okuhara, Ng. Anh Vu Doan, Hideharu Amano, "Body Bias Optimization for Variable Pipelined CGRA", 27th International Conference on Field-Programmable Logic and Applications(FPL), Belgium, September 2017. [[IEEE Xplore]](https://ieeexplore.ieee.org/document/8056851)

## Installation
Please see [Installation guide](./docs/installation_guide.md)

## Included architecture definitions
GenMap supports the following CGRA architectures by default:
1. CMA-SOTB2 [[K.Masuyama, *et al*]](https://ieeexplore.ieee.org/abstract/document/7393280) (a.k.a. NVCMA [[T.Ikezoe, *et al*]](https://ieeexplore.ieee.org/abstract/document/8641712) )
1. CC-SOTB [[Y.Matsushita, *et al*]](https://ieeexplore.ieee.org/abstract/document/7577346) 
1. CC-SOTB2 (VPCMA) [[N.Ando, *et al*]](https://ieeexplore.ieee.org/abstract/document/7929537) 
1. VPCMA2 [[T.Kojima, *et al*]](https://ieeexplore.ieee.org/abstract/document/9034924) 
1. RHP-CGRA [[A.Podobas, *et al*]](https://ieeexplore.ieee.org/abstract/document/9153262)

Architecture information and parameters for some simulations are in the [chip_files](./chip_files)

## Quick Tutorial
This tutorial introduces you to GenMap overview.

### Run GenMap
First, make a working directory. In this tutorial, the working directory is in the same directory as the GenMap.
```
(GenMap_env) # mkdir work
(GenMap_env) # cd work
```

Please copy a sample application DFG file to a working directory (*gray* in this example).
```
(GenMap_env) # cp ../GenMap/app_samples/gray.dot ./
```

Please copy the architecture definition file and simulation parameter file to the working directory (*CCSOTB2* in this example).
```
(GenMap_env) # cp ../GenMap/chip_files/CCSOTB2/arch.xml ./
(GenMap_env) # cp ../GenMap/chip_files/CCSOTB2/simdata.xml ./
```

Please copy the optimization setting to the working directory.
```
(GenMap_env) # cp ../GenMap/OptimizationParameters.xml ./
```

To run GenMap, please execute:
```
(GenMap_env) # python3 ../GenMap/GenMap.py gray.dot 10 [--nproc num]
```
At least, you have to specify a path to an application DFG file as a positional argument.
For other optional arguments, please see help (``python GenMap.py -h``)
You can specify the process count for multiprocessing (default 1).

After GenMap starts, the optimization status will appear like below.
```
Generation 121:  40%|█▌  | 120/300 [1:20:02<2:07:56, 42.65s/it, hof_len=97, stall=6]
Wire_Length: , max=29, min=27                                                       
Mapping_Width: , max=3, min=2                                                       
Op_Mapping_Width: , max=3, min=2                                                    
Power_Consumption: , max=0.589, min=0.347                                           
Time_Slack: , max=61.2, min=0.462    
```


## Generate Configuration
If the above optimization finishes successfully, it will save a result *gray.dump* (in default).
By loading this result, you can generate configuration data for the architecture.

Please execute:
```
(GenMap_env) # python3 ../GenMap/CCSOTB2_ConfGen.py gray.dump
```

Then a shell will start.
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

To save the configuration, execute:
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

You can see the usage of these commands in GenMap Shell with ``--help`` option as follows.

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


## Detailed documentation
Please refer to [[docs]](./docs/index.md)