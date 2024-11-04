# DLBench

## Usage

### Benchmark a run

#### Examples

##### Souffle
Souffle in interpreter mode
``` sh
./dlbench.py run "souffle -j 4 -F test -D test test/reachable.dl"
```

Souffle in compiled mode
``` sh
./dlbench.py run "test/sou-reachable"
```
##### DDlog

``` sh
./dlbench.py run "./ddlog-test/reachable_ddlog/target/release/reachable_cli -w 4 < ddlog-test/edge.facts"
```
##### RecStep


### Plot runs

#### Plot a run

``` sh
./dlbench.py plot --logs "dlbench-sou-reachable.log"
```

#### Plot and compare multiple runs

``` sh
./dlbench.py plot --logs "dlbench-sou-reachable.log" "dlbench-ddlog-reachable.log" 
```
#### Plot and compare last n runs

``` sh
./dlbench.py plot --last <n>
```
``` sh
./dlbench.py plot --last 1
```
``` sh
./dlbench.py plot --last 3
```
