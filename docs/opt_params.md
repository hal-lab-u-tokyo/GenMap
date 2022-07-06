# Optimization Settings
Settings for the genetic algorithm are passed using an XML file.

The format as follows:

```
<Config>
	<Router>RouterClassName</Router>
	<eval [args='{"key1": value, "key2": value}'] >Objective1</eval>
	<eval [args=...] >Objective2</eval>
	....
	<parameter name="param1" >param_value</parameter>
	<parameter name="param2" >param_value</parameter>
	...
</Config>
```

The top level element must be `<config>` element.

## *Router* element
The XML file can have only an element of this tag. It specifies a class handling routing algorithm. This repositoy contains `AStartRouter` class. A detailed description of the routing algorithm is available in the published paper.

For those who want to use their own algorithm, please implement a class derived from `RouterBase`.

## *eval* element
GenMap is based on NSGA2 so that it can optimize solutions for multiple objectives.
An `eval` element enables an objective function for optimization.
Each objective function is implemented as a class.
The inner text of the element must be identical to the class name.
If there is no matched class, the setting up process will be aborted.

In addition, extra arguments for each objective can be passed with `args` attribute.
The attribute value is a string corresponding to a python dictionary like the above example.

Currently, `*Eval` classes in this repository are available.
For those who want to add their own objective, please refer to [[this page]](./add_objective.md).


## *parameter* element
A `parameter` element changes a parameter in the genetic algorithm instead of the default ones.

|name|description| default|
|:----|:----|:----:|
|"Maximum generation"|Maximum generation size for termination condition|300|
|"Minimum generation"|Minimum generation size before termination|30|
|"Maximum stall"|Maximum stall count for termination condition|100|
|"Initial population size"|The size of initial solutions|300|
|"Offspring size"|The size of generated offspring solutions for each generation|100|
|"Select size"|The size of selected solutions for the next generation|45|
|"Random population size"|The size of randomly generated solution added for each generation|10|
|"Crossover probability"|The probability of crossover|0.7|
|"Mutation probability"|The probability of mutation|0.3|
|"Local mutation probability"|The probability of the mutation process within mapped PEs|0.5|
|"Initial place iteration"|Trial count to create a valid initial placement|100|
|"Initial place count"|The size of prepared initial placement|200|
|"Random place count"|The size of prepared random placement|100|
|"Topological sort probability"|The probability of applying topological sort for created random mapping |0.5|

