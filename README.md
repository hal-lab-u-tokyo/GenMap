# GenMap
Application Mapping Framework for CMA using Genetic Algorithm

# Installation Requirements
GenMap requires some additional packages. So, you have to have root privileges to install them.

### Supported OS
1. CentOS 7

### Required Packages
1. git
1. python36  
1. python36-devel 
1. python36-libs  
1. python36-tkinter 
1. graphviz

## Install Steps
We recommend to install GenMap on a virtual python environment to avoid python library conflicts.

1. Install above packages (as necessary)
```
 $ yum install git python36 python36-devel python36-libs python36-tkinter graphviz
```
Perhaps, you need to add a yum repository to install python3.
```
sudo yum install https://centos7.iuscommunity.org/ius-release.rpm
```

2. Build a virtual python environment
```
# pyvenv-3.6 GenMap_env
```
It will create "GenMap_env" directory. You can use your favorite directory name.

3. Activate the virtual environment
```
# cd GenMap_env
# source bin/activate
```
If you want to exit this environment, just execute ``deactivate`` command.

4. Install Python Libraries
GenMap requires the following python libraries. Recommended version for each library is in the bracket.
    1. deap (1.0.1)
    1. pulp (1.6.8)
    1. networks (2.2)
    1. tqdm (4.31.1)
    1. matplotlib (3.0.0)
    1. pydot (1.4.1)
    1. pygmo (2.9)
    1. prettytable (0.7.2)
```
(GenMap_env) # pip3 install (package_name)[==version]
```
 
 5. Install GenMap
 ```
(GenMap_env) # git clone git@github.com:hungalab/GenMap.git
```

# Supported Architectures
GenMap supports following CMA architectures by default:
    1. CMA-SOTB2
    1. CC-SOTB
    1. CC-SOTB2 (VPCMA)

Architecture information and parameters for some simulation are in the [chip_files](./chip_files)

# Quick Tutorial
This tutorial introduces you to GenMap overview.

## Run GenMap
At first, make a working directory. In this tutorial, the working directory is in the same directory as the GenMap.
```
(GenMap_env) # mkdir work
(GenMap_env) # cd work
```

Please copy a sample application file to working direcotry (*gray* in this example).
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
(GenMap_env) # cp ../GenMap/OptimizationParamters.xml ./
```

To run GenMap, please execute:
```
(GenMap_env) # python3 ../GenMap/GenMap.py gray.dot 10 
```
At least, you have to specify two arguments. First is application source file, and second is operation frequency (default MHz).
For other optional arguments, please see help (``python GenMap.py -h``)

After GenMap starts, optimization status will appear like below.
```
Generation 121:  40%|█▌  | 120/300 [1:20:02<2:07:56, 42.65s/it, hof_len=97, stall=6]
Wire_Length: , max=29, min=27                                                       
Mapping_Width: , max=3, min=2                                                       
Op_Mapping_Width: , max=3, min=2                                                    
Power_Consumption: , max=0.589, min=0.347                                           
Time_Slack: , max=61.2, min=0.462    
```

## Generate Configuration
If the above optimization finishs successfully, it will save a result *gray.dump* (in default).
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

# Write an Application 
For GenMap, an application data-flow is described in *DOT* format.
For more information, please refer to [To Be Add]()

# How to customize 
You can customize the followings.
1. Architecutes
    1. PE Size
    1. PE Array Topology  
    etc.
1. Optimization objectives
1. Routing algorithm

For more information, please refer to [To Be Add]()
