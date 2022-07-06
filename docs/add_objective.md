# Add a new objective
As explained in Section: [Optimization settings](./opt_params.md),
each objective function is implemented as a class.
The class needs to be derived from an abstract class `EvalBase` and execute the following static methods:
1. `eval(CGRA, app, sim_params, individual, **info)`
It returns an evaluated value of the objective function.
* Arguments
	* CGRA [PEArrayModel](../PEArrayModel.py): A model of the target CGRA
	* app [Application](../Application.py): An application to be optimized
	* sim_params [SimParameters](../SimParameters.py): parameters for some simulation
	* individual [Individual](../Individual.py): An indivisual to be evaluated
	* info: a dictionary passed from OptimizationParamater file of `args`

1. `isMinimize()`
It specifies whether the value of this objective should be minimized or maximized.
For minimization, it returns `True`.

1. `name()`
It returns a string of name of the objective function.

# Code snippet
Here is an example code to make a 2D array whose element corresponds to a PE.

```
SEs = [v for v in individual.routed_graph.nodes() if CGRA.isSE(v)]
ALUs = [v for v in individual.routed_graph.nodes() if CGRA.isALU(v)]
width, height = CGRA.getSize()
for node in SEs + ALUs:
	for x in range(width):
		for y in range(height):
			rsc = CGRA.get_PE_resources((x, y))
			if node in  [v for se_set in rsc["SE"].values() for v in se_set ] or \
				node == rsc["ALU"]:
				x_coords.append(x)
				break
```
`individual.routed_graph` returns an graph representation of PnR result where the nodes are hardware resources such as ALU, switch elements.

The first two line obtain used switch elements and ALUs.
The nested for-loop creates a 2D array corresponding to PE array.
Each element indicates used resources (nodes in the result graph) in a PE.


# Data storage 
An instance of the `Individual` has an interface to store some evaluated values in addition to the returned value.

* `Individual.saveEvaluatedData("key", data)`

The stored data will be exported in the configuration generation.


