# Termination condition
The genetic algorithm will stop evolution when satisfying any of the following conditions:
1. Reaching the maximum generation (``Maximum generation``)
1. No improvement during a specified generation (``Maximum stall``)

However, the optimization will not be terminated until the minimum generation count  (``Minimum generation``), even if the above condition is met.

# Stop optimization manually before reaching the termination condition

If you want to exit the optimization before satisfying the above condition,
send ``USR1`` signal to the main process as follows.

```
$ kill -USR1 {PID of GenMap}
```

PID will be shown in the launch message.