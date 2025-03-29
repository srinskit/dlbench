# DLBench

A utility to monitor, plot and compare resource utilization of programs.

## Install

```sh
git clone https://github.com/srinskit/dlbench

pip install --user dlbench/
```

## Uninstall

```sh
pip uninstall dlbench
```

## Usage

### Benchmark a run

`dlbench run` takes as input a shell command `cmd` that would execute the benchmark target. It starts the benchmark target as a subprocess and monitors it's resource utilization. DLBench monitors the CPU utilization, memory utilization and disk reads of the benchmark target and any subprocess of the target. Additional `systemd` background processes can be monitored by specifiying their names in the `--monitor` argument. The reported utilization for any metric is the sum of utilizations of all the above processes.

`dlbench run` also takes as input a string `tag`, which is used to label the following files created by DLBench:
* The resource utilization metrics are stored into a `<tag>.log` file. 
* The output (`stdout`) of the target is stored into a `<tag>.out` file.

Specifying the option `--suffix-time` will append a timestamp to the tag to make it unique.

```sh
dlbench run --help

usage: dlbench run [-h] [--suffix-time] [--monitor MONITOR [MONITOR ...]] cmd tag

positional arguments:
  cmd                   Shell command that would execute the benchmark target
  tag                   Name to tag the results with

options:
  -h, --help            show this help message and exit
  --suffix-time         Suffix the tag with a timestamp
  --monitor MONITOR [MONITOR ...], -m MONITOR [MONITOR ...]
                        Names of systemd processes to monitor in addition to benchmark target
```

`dlbench plot` is used to plot resource utilization data from one or more `<tag>.log` files. If multiple log files are specified, their resource utilization is plotted on the same chart for comparison. 

Log files can be specified with the `--logs` argument. File names and patterns are accepted. Alternatively, `--last <n>` can be used to plot the `n` most recent log files in the current working directory.

The `--metrics` argument can be used to specify what charts are plotted. For example, `--metrics c` plot only the CPU utilization and `--metrics cr` plots the CPU utilization and disk reads. The `--pretty` flag is used to remove outliers and smooth the plot.

```sh
dlbench plot --help

usage: dlbench plot [-h] [--pretty] [--graphs GRAPHS] (--logs LOGS [LOGS ...] | --last LAST)

options:
  -h, --help            show this help message and exit
  --pretty, -p          Denoise and plot
  --graphs GRAPHS, -g GRAPHS
                        Graphs to plot (c: CPU, m: memory, r: disk reads)
  --logs LOGS [LOGS ...]
                        Path to log files of runs
  --last LAST           Plot recent runs
```

### Examples

#### Sample

Benchmark sample program with argument `5`:
```sh
dlbench run "./testproc.sh 5" test1
```

```sh
Run name: test1
Started process: testproc.sh
Logging stats to: test1.log
STATS: (37.16, 0.0, 954368, 185811385, 2)
```
```sh
ls test1*

test1.log  test1.out
```

Plot the log file:

```sh
dlbench plot --logs test1.log
```

![sample plot](sample1.png)


Benchmark sample program with argument `7`:

```sh
dlbench run "./testproc.sh 7" test2
```

Plot results of both runs:

```sh
dlbench plot --logs test1.log test2.log

# or

dlbench plot --logs test*.log

# or

dlbench plot --last 2
```

![sample plot](sample2.png)

Plot only memory utilization:

```sh
dlbench plot --logs test*.log --metrics m
```

![sample plot](sample3.png)


#### Souffle
Souffle in interpreter mode
``` sh
dlbench run "souffle -j 4 -F test -D test reach.dl" "reach_4_souffle-intptr" 
```

Souffle in compiled mode
``` sh
dlbench run "./souffle-reach -F test" "reach_souffle-cmpl"
```

#### RecStep

Monitor the QuickStep database process in-addition to RecStep.

```sh
dlbench run "recstep --program reach.dl --input /data --jobs 64" "reach_64_recstep" -m quickstep_cli_shell
```

#### DDlog

Supply inputs to the benchmark target process using input redirections.

``` sh
dlbench run "./reach_ddlog/target/release/reach_cli -w 4 < ddlog-test/edge.facts" "ddlog"
```


### Understanding the plot

![sample plot](sample4.png)

In the above plot:

* The first chart plots vs time the cumulative CPU utilization, i.e., sum of the instantaneous CPU utlization (percent) of all worker threads in the target process. Cumulative utilization was chosen to minimize cluter when comparing multiple runs.
* The second chart plots vs time the instantaneous memory utilization of the process.
* The final chart plots vs time the total disk reads by the process.
