# Installation Guide
## Requirements
GenMap requires some additional packages. So, you have to have root privileges to install them.

## Confirmed OS
1. CentOS 7
1. CentOS 8

We provide a docker image to use this tool easily.
So, if you can use docker, we recommend using it.
You will be freed from complicated environment construction.
Also, it will be helpful to use GenMap in another OS.
See [HowToUseDocker](../docker/HowToUseDocker.md) for more details.

## Required Packages/Libraries
1. git
1. python36
1. python36-devel
1. python36-libs
1. python36-tkinter
1. graphviz

## Install Steps
We recommend installing GenMap on a virtual python environment to avoid python library conflicts.

Install the above packages (as necessary)

For CentOS7,
```
 $ yum install git python36 python36-devel python36-libs python36-tkinter graphviz cmake3
```

For CentOS8,
```
 $ dnf install git python36 python36-devel python3-libs python3-tkinter graphviz cmake3
```

Perhaps, you need to add a yum repository to install python3.
```
$ sudo yum install https://centos7.iuscommunity.org/ius-release.rpm
```

2. Build a virtual python environment
```
$ pyvenv-3.6 GenMap_env
```
It will create a "GenMap_env" directory. You can use your favorite directory name.

3. Activate the virtual environment
```
$ cd GenMap_env
$ source bin/activate
```
If you want to exit this environment, just execute ``deactivate`` command.


4. Install GenMap
 ```
(GenMap_env) $ git clone git@github.com:hungalab/GenMap.git
```

5. Install Python Libraries
GenMap requires the following python libraries. Recommended version for each library is in the bracket.
    1. deap (1.0.1)
    1. pulp (2.4)
    1. networkx (2.2)
    1. tqdm (4.31.1)
    1. matplotlib (3.0.0)
    1. pydot (1.4.1)
    1. pygmo (2.9)
    1. prettytable (0.7.2)
    1. cvxpy (1.1.10)
    1. seaborn (0.11.1)
    * Optional
    1. llvmlite (0.30.0) (necesssary to export configuration as LLVM-IR)
    1. pyeda (0.28.0) (necessary for configuration compression using espresso)
    1. mosek (9.2.38) (necessary to use mosek's solvers)

```
(GenMap_env) $ pip3 install (package_name)[==version]
```
 or
 ```
 (GenMap_env) $ pip3 install -r requirements.txt (in this repo)
 # Perhaps a version conflict will occur between numpy and cvxpy
 # In this case, please install only numpy at first. Then, try to install the other packages with requirements.txt
 # The optional packages are commented out
 ```