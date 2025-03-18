#!/bin/bash

start_time=$(date +%s)
while [ $(($(date +%s) - start_time)) -lt 60 ]; do
    cycle_start=$(date +%s)
	echo running
    while [ $(($(date +%s) - cycle_start)) -lt 5 ]; do :; done
	echo sleeping
    sleep 5
done
