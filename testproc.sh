#!/bin/bash

sleep_time=$1
start_time=$(date +%s)

while [ $(($(date +%s) - start_time)) -lt 30 ]; do
    cycle_start=$(date +%s)
	echo running
    while [ $(($(date +%s) - cycle_start)) -lt $sleep_time ]; do :; done
	echo sleeping
    sleep $sleep_time
done
