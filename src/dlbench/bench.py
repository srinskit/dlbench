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
    target_process = None

    retry = 5
    while retry > 0:
        children = psutil.Process(sh.pid).children(recursive=True)

        if len(children) == 1:
            target_process = children[0]
            break
        elif len(children) > 1:
            print("Warning: benchmark target command led to multiple processes, monitoring the last one")
            target_process = children[-1]
            break

        retry = retry - 1
        time.sleep(2)

    if target_process is not None:
        print("Started process:", target_process.name())

    return sh, target_process

def benchmark(run_name, sh, target_process, start_time, misc_targets):
    with open(run_name + '.log', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Time', 'CPU Percent', 'MEM Usage', 'IO Reads'])
        dt = .05
        t = 0

        while sh.poll() is None:
            t = round(time.time() - start_time, 2)
            targets = [
                target_process,
                *target_process.children(recursive=True),
            ]

            if misc_targets is not None and len(misc_targets) > 0:
                systemd = psutil.Process(1)
                for child in systemd.children(recursive=False):
                    if child.name() in misc_targets:
                        targets.append(child)

            for proc in targets:
                try:
                    with proc.oneshot():
                        cpu_percent = proc.cpu_percent() # cumulative across all CPU
                        mem_bytes = proc.memory_info().data # phy mem used by data sections
                        io_read_bytes = proc.io_counters().read_chars # cumulative bytes read (includes non-disk-io)

                except psutil.NoSuchProcess:
                    # Ignore if process terminated
                    pass

            row = (t, cpu_percent, mem_bytes, io_read_bytes)
            writer.writerow(row)
            print(f"\rSTATS:", row, end='', flush=True)

            if dt < 1 and t > 100 * dt:
                dt = min(2 * dt, 1)

            # 00s - 05s: dt = 0.05s
            # 05s - 10s: dt = 0.1s
            # 10s - 20s: dt = 0.2s
            # 20s - 40s: dt = 0.4s
            # 40s - 80s: dt = 0.8s
            # 80s - inf: dt = 1s

            time.sleep(dt) 
            t += dt

    print()

def plot_run(run_names):
    fig, [cpu_ax, mem_ax, io_ax] = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'orange', 'purple', 'brown']

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

    io_ax.set_xlabel('Time (s)')

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


