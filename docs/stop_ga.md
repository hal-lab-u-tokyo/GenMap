# Termination condition
The genetic algorithm will stop evolution when satisfying any of the following conditions:
1. Reaching the maximum generation (``Maximum generation``)
1. No improvement during a specified generation (``Maximum stall``)
1. Any solution whose fitness value exceeds a threshold found

However, the optimization will not be terminated until the minimum generation count  (``Minimum generation``), even if the above condition is met.

## How to specify the threshold
When a user wants to set a threshold for fitness of an objective function "Objective1", please pass an argument to the evaluation class in the optimization parameter XML file as follows:
```
<eval [args='{"threshold": 1.0}'] >Objective1</eval>
```
If the objective function is minimization and when a solution with a fitness value lower than 1.0 is found, the genetic algorithm will stop.


# Stop optimization manually before reaching the termination condition

If you want to exit the optimization before satisfying the above condition,
send ``USR1`` signal to the main process as follows.

```
$ kill -USR1 {PID of GenMap}
```

PID will be shown in the launch message.