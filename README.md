# DLBench

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

#### Examples

##### Souffle
Souffle in interpreter mode
``` sh
dlbench run "souffle -j 4 -F test -D test test/reachable.dl"
```

Souffle in compiled mode
``` sh
dlbench run "test/sou-reachable"
```
##### DDlog

``` sh
dlbench run "./ddlog-test/reachable_ddlog/target/release/reachable_cli -w 4 < ddlog-test/edge.facts"
```
##### RecStep


### Plot runs

#### Plot a run

``` sh
dlbench plot --logs "dlbench-sou-reachable.log"
```

#### Plot and compare multiple runs

``` sh
dlbench plot --logs "dlbench-sou-reachable.log" "dlbench-ddlog-reachable.log" 
```
#### Plot and compare last n runs

``` sh
dlbench plot --last <n>
```
``` sh
dlbench plot --last 1
```
``` sh
dlbench plot --last 3
```
