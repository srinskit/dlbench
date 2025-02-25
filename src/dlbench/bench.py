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


def start_target(shell_cmd, f):
    # TODO: set process priority for better bench
    # TODO: set CPU affinity for consistent bench

    sh = subprocess.Popen(shell_cmd, shell=True, stdout=f)
    target_process = None

    retry = 5
    while retry > 0:
        children = psutil.Process(sh.pid).children(recursive=True)

        if len(children) == 1:
            target_process = children[0]
            break
        elif len(children) > 1:
            print(
                "Warning: benchmark target command led to multiple processes, monitoring the last one"
            )
            target_process = children[-1]
            break

        retry = retry - 1
        time.sleep(2)

    if target_process is not None:
        print("Started process:", target_process.name())

    return sh, target_process


def benchmark(run_name, sh, target_process, start_time, misc_targets):
    print("Logging stats to:", run_name + ".log")
    with open(run_name + ".log", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Time", "CPU Percent", "MEM Usage", "IO Reads", "_NProc"])
        dt = 0.05
        t = 0

        targets = [target_process]
        pid_map = {target_process.pid: True}

        while sh.poll() is None:
            t = round(time.time() - start_time, 2)

            for proc in target_process.children(recursive=True):
                if proc.pid not in pid_map:
                    targets.append(proc)
                    pid_map[proc.pid] = True

            if misc_targets is not None and len(misc_targets) > 0:
                systemd = psutil.Process(1)
                for proc in systemd.children(recursive=False):
                    if proc.name() in misc_targets and proc.pid not in pid_map:
                        targets.append(proc)
                        pid_map[proc.pid] = True

                    # TODO: add children of background process too

            cpu_percent = 0
            mem_bytes = 0
            io_read_bytes = 0

            for proc in targets:
                try:
                    with proc.oneshot():
                        cpu_percent += proc.cpu_percent()  # cumulative across all CPU
                        mem_bytes += (
                            proc.memory_info().data
                        )  # phy mem used by data sections
                        io_read_bytes += (
                            proc.io_counters().read_chars
                        )  # cumulative bytes read (includes non-disk-io)

                except psutil.NoSuchProcess:
                    if proc.pid == target_process.pid:
                        print("[dlbench] target missing")
                    else:
                        targets = list(filter(lambda p: p.pid != proc.pid, targets))
                        pid_map[proc.pid] = False

            row = (t, cpu_percent, mem_bytes, io_read_bytes, len(targets))
            writer.writerow(row)
            print(f"\rSTATS:", row, end="", flush=True)

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


def plot_run(run_names, args):
    fig, [cpu_ax, mem_ax, io_ax] = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    colors = ["b", "g", "r", "c", "m", "y", "k", "orange", "purple", "brown"]
    graph_lines = [[] for _ in range(3)]

    for run, clr in zip(run_names, colors):
        data = pd.read_csv(run + ".log")

        # Cleanup data
        # if args.pretty:
        #     Q1 = data["CPU Percent"].quantile(0.25)
        #     Q3 = data["CPU Percent"].quantile(0.75)
        #     IQR = Q3 - Q1
        #     upper_bound = Q3 + 2 * IQR
        #     print(run, upper_bound)
        #     data = data[data["CPU Percent"] < upper_bound]

        (line,) = cpu_ax.plot(
            data["Time"], data["CPU Percent"], label=run, linestyle="-", color=clr
        )
        graph_lines[0].append(line)
        (line,) = mem_ax.plot(
            data["Time"],
            data["MEM Usage"] / 1000.0 / 1000.0,
            label=run,
            linestyle="-",
            color=clr,
        )
        graph_lines[1].append(line)
        (line,) = io_ax.plot(
            data["Time"], data["IO Reads"] / 1000.0, label=run, color=clr
        )
        graph_lines[2].append(line)
        # io_ax.plot(data['Time'], data['IO Writes'], label='Writes (' + run + ')', color=clr, linestyle='--', marker='x')

    cpu_ax.set_title("Cumulative CPU Usage")
    mem_ax.set_title("Memory Usage")
    io_ax.set_title("Disk Reads")

    cpu_ax.set_ylabel("Percent")
    mem_ax.set_ylabel("MB")
    io_ax.set_ylabel("KB")

    io_ax.set_xlabel("Time (s)")

    legends = [
        cpu_ax.legend(),
        mem_ax.legend(),
        io_ax.legend(),
    ]

    # Define function for toggling visibility
    def on_legend_click(event):
        for legend, lines in zip(legends, graph_lines):
            for leg_line, leg_text, line in zip(
                legend.get_lines(), legend.get_texts(), lines
            ):
                if event.artist == leg_text:
                    visible = not line.get_visible()
                    line.set_visible(visible)
                    leg_line.set_alpha(1.0 if visible else 0.2)
                    leg_text.set_alpha(1.0 if visible else 0.3)
                    fig.canvas.draw()
                    plt.draw()
                    return

    # Connect event
    fig.canvas.mpl_connect("pick_event", on_legend_click)

    # Make legend elements clickable
    for leg in legends:
        for leg_text in leg.get_texts():
            leg_text.set_picker(True)

    cpu_ax.grid()
    mem_ax.grid()
    io_ax.grid()

    # plot_name = run_names[0]

    # if len(run_names) > 1:
    #     plot_name = run_names[0] + "-cmp"

    fig.canvas.manager.set_window_title("DlBench")

    manager = plt.get_current_fig_manager()
    manager.full_screen_toggle()

    plt.tight_layout()
    # plt.savefig(plot_name, dpi=300)
    plt.show()


def find_latest_logs(dir, n):
    search_pattern = os.path.join(dir, f"*.log")
    files = glob.glob(search_pattern)

    if not files:
        return None

    files.sort(reverse=True, key=os.path.getmtime)
    return files[:n]


def cleanup():
    for child in psutil.Process().children(recursive=True):
        try:
            if child.is_running():
                child.kill()
        except Exception as e:
            print(f"[bench.cleanup] An error occurred: {e}")
