## Running Optimization
### Needed files
* Application file
	* sample: [gray-scale filter](../app_samples/gray.dot)
	* Reference: [Application writing guide](./write_app.md)
* Architecture definition file
	* sample: [CC-SOTB2](../chip_files/CCSOTB2/arch.xml)
	* Reference: [Add your CGRA design](./add_design.md)
* Simulation parameters file
	* sample: [CC-SOTB2](../chip_files/CCSOTB2/simdata.xml)
	* Reference: [Prepare your simulation parameters to evaluate the solution](./add_param.md)
* Optimization parameters file
	* sample: [OptimizationParameters.xml](../OptimizationParameters.xml)
	* Reference: [Setting optimization](./opt_params.md)

### Usage
```
$ python3 GenMap.py <app_file> [options...]
```
At least, you have to specify a path to an application DFG file as a positional argument.

It implicitly loads `arch.xml`, `simdata.xml`, `OptimizationParameters.xml` in the working directory for the above needed files.
If you want to specify other paths, please use the following options:
* `--arch`: path to the architecture definition file
* `--simdata`: path to the simulation parameter file
* `--opt-conf`: path to the optimization parameters file

After GenMap starts, the optimization status will appear as below.
```
Generation 121:  40%|█▌  | 120/300 [1:20:02<2:07:56, 42.65s/it, hof_len=97, stall=6]
Wire_Length: , max=29, min=27                                                       
Mapping_Width: , max=3, min=2                                                       
Op_Mapping_Width: , max=3, min=2                                                    
Power_Consumption: , max=0.589, min=0.347                                           
Time_Slack: , max=61.2, min=0.462    
```

### Other options
* `--freq`: an operational frequency
* `--freq-unit`: the prefix of frequency unit (k, M, G) (Default: M)
* `-o, --output`: output file name (default: {app_name}.dump)
* `--init-map`: method to generate initial solutions
	* `graphviz`: based on *DOT* algorithm
`tsort`based on the topological sort
	* `random`: fully randomized
* `--log`: file to save the evolution log
* `--nproc`: the number of multi-process (default: 1)
	* Initialization and evaluation phase are parallelized
* `--data-flow`: data flow direction information for CGRAs in which data flows are restricted to a certain direction
	* `left-right`: only data flowing in the right direction
	* `right-left`: only data flowing in the left direction
	* `bottom-top`: only data flowing in the upwards direction
	* `top-bottom`: only data flowing in the downwards direction
	* `horizontal`: data flowing in both the right and left directions
	* `vertical`: data flowing in both the upwards and downwards directions
	* `any`: there is no limitation in the data flow direction (default)

## See the optimization result & generate configuration
After saving the optimization results (dump file),
you can see the results with configuration generator scripts derived from `ConfGenBase` class.

`Generic_ConfGen.py` is a general script to save the configuration in JSON format.
In this instruction, this script is used.

```
$ python3 Generic_ConfGen.py <dump_file>
```
When the above command is executed, a shell called *GenMapShell* appears.
```
=== GenMap solution selection utility ===
GenMap shell>   
```

To show all solutions, please use *show* command

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

### Available commands in GenMapShell
In the GenMap Shell, the following commands are available.
1. show: show the result
1. sort: sort the solutions by specified objective
1. filter: filter the solutions with some conditions
1. select: select a solution
1. reset: reset the filtering and selection
1. view: view mapping of the selected solution
1. save: save configurations of the selected solution
1. report_hypervolume: make a report of hypervolume history
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

### Saved files
With `Generic_ConfGen.py`, the following files are created:

* {app_name}_conf.json: configuration data and some other information
* {app_name}_map.png: mapping figure
* {app_name}_hist.png: histogram of latency difference
* {app_name}_heat.png: heatmap of latency difference

### Style options for `Generic_ConfGen.py`
In the `save` command, the following style options are available

* `-s origin=pos`: position of origin coordinate to illustrate the mapping figure
	* available values: `bottom-left`, `top-left`, `bottom-right`, `top-right`
* `-s readable`: saving the JSON data with human-readable format instead of raw configuration values