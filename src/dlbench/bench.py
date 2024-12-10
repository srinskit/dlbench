#!/usr/bin/python3

import subprocess
import matplotlib.pyplot as plt
import psutil
import csv
import time
import pandas as pd
import os
import glob

def print_sys_metadata():
    print("System CPU count:", psutil.cpu_count())

    mem = psutil.virtual_memory()
    print("System MEM total:", int(round(mem[0] / 1024.0 / 1024.0 / 1024.0, 2)))
    print("System MEM avail:", int(round(mem[1] / 1024.0 / 1024.0 / 1024.0, 2)))
    print("System MEM usage:", mem[2])
    
    
def start_target(shell_cmd):
    # TODO: set process priority for better bench
    # TODO: set CPU affinity for consistent bench
    
    sh = subprocess.Popen(shell_cmd, shell=True)
    target_process = psutil.Process(sh.pid).children()[0]
    print("Started process:", target_process.name())
    return sh, target_process

def gen_run_name(target_process):
    local_time = time.localtime()
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", local_time)
    return 'dlbench-' + target_process.name() + '-' + timestamp

def benchmark(run_name, sh, target_process):
    with open(run_name + '.log', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Time', 'CPU Percent', 'MEM Usage', 'IO Reads'])

        t = 0
        dt = 500
        cpu_time = None
        
        while sh.poll() is None:
            with target_process.oneshot():
                cpu_time = target_process.cpu_times()  
                cpu_percent = target_process.cpu_percent() # cumulative across all CPU
                mem_bytes = target_process.memory_info().data # phy mem used by data sections
                io_read_bytes = target_process.io_counters().read_chars # cumulative bytes read (includes non-disk-io)
                io_write_bytes = target_process.io_counters().write_chars # cumulative bytes wrote (includes non-disk-io)
                row = (t, cpu_percent, mem_bytes, io_read_bytes)
                writer.writerow(row)
                print(f"\rSTATS:", row, end='', flush=True)

            t += dt
            time.sleep(dt / 1000.0) 
        
        print()        
        print('CPU Time:', cpu_time)
        print('CPU Time:', sum(cpu_time[:-1]))
        
        
    # TODO calculate a benchmark score
    #   * based on CPU time
    #   * based on IO
    #   * based on MEM

def plot_run(run_names):
    fig, [cpu_ax, mem_ax, io_ax] = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    colors = ['r', 'g', 'b' , 'y']

    for run, clr in zip(run_names, colors):
        data = pd.read_csv(run + '.log')
        cpu_ax.plot(data['Time'], data['CPU Percent'], label=run, linestyle='-', color=clr)
        mem_ax.plot(data['Time'], data['MEM Usage'] / 1024.0 / 1024.0, label=run, linestyle='-', color=clr)
        io_ax.plot(data['Time'], data['IO Reads'], label='Reads (' + run + ')', color=clr)
        # io_ax.plot(data['Time'], data['IO Writes'], label='Writes (' + run + ')', color=clr, linestyle='--', marker='x')

    cpu_ax.set_title('Cumulative CPU Usage')
    mem_ax.set_title('Memory Usage')
    io_ax.set_title('IO')
    
    cpu_ax.set_ylabel('Percent')
    mem_ax.set_ylabel('MB')
    io_ax.set_ylabel('Bytes')

    io_ax.set_xlabel('Time (ms)')

    cpu_ax.legend()
    mem_ax.legend()
    io_ax.legend()

    cpu_ax.grid()
    mem_ax.grid()
    io_ax.grid()
    
    plot_name = run_names[0]
    
    if len(run_names) > 1:
        plot_name = run_names[0] + '-cmp'
   
    fig.canvas.manager.set_window_title('DlBench ' + plot_name)
    
    manager = plt.get_current_fig_manager()
    manager.full_screen_toggle()

    plt.tight_layout()
    plt.savefig(plot_name, dpi=300)
    plt.show()


def find_latest_logs(dir, n):
    search_pattern = os.path.join(dir, f'*.log')
    files = glob.glob(search_pattern)

    if not files:
        return None

    files.sort(reverse=True, key=os.path.getmtime)
    return files[:n]


