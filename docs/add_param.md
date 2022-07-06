# Simulation parameters

The file needs to contain at least the following information:
1. Bias range
1. Timing information
1. Power information

If the user is not interested in these values and does not use them for any fitness functions,
please fill those fields with worthless values.

# Structure of XML file
```
<DATA>
	<BiasRange>
		<bias>0.0</bias>
		...
	</BiasRange>
	<Delay unit="ns">
		<ALU bias="0.0" op="add">12.3</ALU>
		...
		<SE bias="0.0">4.5</SE>
		...
	</Delay>
	<Power>
		<Static>
			<PE bias="0.0" unit="mW">1.2</PE>
		</Static>
		<Dynamic>
			<Energy >
		</Dynami>
	</Power>
	<User name="database1">
		<param name="key" type=...>...</param>
		...
	</User>
</DATA>
```

The top-level element must be only a `<DATA>` element.

## BiasRange
The `<BiasRange>` element contains several `<bias>` elements, which are list of available body bias voltage.
The inner text of the `<bias>` is the bias voltage value (float).
At least one voltage is needed.

## Delay
The `<Delay>` element has timing information of ALUs and routing resources for each bias voltage.
If the unit (ps, ns, us, ms) is omitted, ns is used as the default unit.
The child element is either `<ALU>` or `<SE>` element.
Both must have a "bias" attribute for bias voltage with which the delay time is associated.
The `<ALU>` element defines the delay time of the ALU.
It usually depends on the operation (instruction) so that the element has "op" attribute to specify the opcode.
The `<SE>` element defines the delay time of the switch element.

## Power
The `<Power>` element has two inner elements `<Static>` and `<Dynamic>`.
The former contains static power consumption data, and the latter contains parameters for the dynamic power model (Please refer to published papers).

### Static power
The `<Static>` defines the static power consumption of a PE for each bias voltage.
A `<PE>` with a "bias" attribute specifies the value of the static power.
If the unit (pW, nW, uW, mW) is omitted, mW is used as the default unit.

### Dynamic power
Five parameters are necessary as children elements of the `<Dynamic>`.
1. `<Energy>`: an energy consumption per switching (default unit: pJ)
2. `<Propagation>`: a propagation factor
3. `<Decay>`: a decay factor
4. `<SE_weight>`: weight to propagate switching from predecessor nodes for SEs.
5. `<Switching>` with "op" attribute: switching count for each operation in ALUs.


## User defined parameter
In addition to the above parameter, the users can add any parameters with `<User>` fields.
A `<User>` elements create a named database, whose name is specified with the "name" attribute.
A parameter in the database is defined with the inner text of a `<param>` element.
"key" attribute is required for a key string to access the parameter.
The default data type is float.
Other supported types are:
1. python primitive types, e.g., int, float, str, etc
2. list or dict of the above types for collection types

For example, an integer type of parameter can be defined by
```
<param name="foo" type="int">123</param>
```

For the collection types, the data type of their elements is also needed like `type=list[int]` and `type=dict[float]`.
In addition, the dict type of parameter requires a "key" attribute.

The following example will create a dictionary `{"bar": 1, "baz": 2}` named "dict_data":
```
<param name="dict_data" type="dict[int]" key="bar">1</param>
<param name="dict_data" type="dict[int]" key="baz">2</param>
```

### Get the parameters in fitness evaluation (classes derived from EvalBase)

The user-defined parameters can be accessed in the [fitness calculation]((./add_objective.md)).

The `eval` method of the evaluation classes gets a `sim_params` as an argument.
It is an instance of [SimParameters](../SimParameters.py) class.
It has a getter method `getUserdata(name)`, which returns the database named "name" as a dictionary.

Assuming the above examples,

```
def eval(CGRA, app, sim_params, individual, **info):
....
userdata = sim_params.getUserdata("database1") # <- get dictionary of user data
x = userdata["foo"] # get 123 of integer
d = userdata["dict_data] # get the dictionary
y = d["bar] # get 1 of integer
z = d["baz"] # get 2 of integer
```

