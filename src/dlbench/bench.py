#!/usr/bin/python3

import subprocess
import matplotlib.pyplot as plt
import psutil
import csv
import time
import pandas as pd
import os
import glob
import re


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


def pretty_parse(log_files):
    seq = [
        ("Flowlog", "Purple", "flowlog", "f", "-"),
        ("Flowlog", "Purple", "eclair", "f", "-"),
        ("Souffle (comp.)", "Navy", "souffle-cmpl", "s", "--"),
        ("Souffle (interp.)", "Lightblue", "souffle-intptr", "i", "--"),
        ("RecStep", "DarkOrange", "recstep", "r", ":"),
        ("DDlog", "FireBrick", "ddlog", "d", "-."),
    ]

    workers_set = set()
    dataset_set = set()
    program_set = set()

    engine = None
    workers = None
    dataset = None
    program = None

    log_map = {}

    for file in log_files:
        features = re.split(r"[/_.]", file.name)
        engine = features[-2]
        workers = features[-3]
        dataset = features[-4]
        program = features[-5]

        workers_set.add(workers)
        dataset_set.add(dataset)
        program_set.add(program)

        error_found = True
        if engine in log_map:
            print("Error: ensure only one log file per engine is supplied")
        elif len(workers_set) != 1:
            print("Error: ensure only one set of workers are compared")
        elif len(dataset_set) != 1:
            print("Error: ensure only one dataset is compared")
        elif len(program_set) != 1:
            print("Error: ensure only one program is compared")
        else:
            log_map[engine] = file
            error_found = False

        if error_found:
            print("Files:\n" + "\n".join([file.name for file in log_files]))
            exit(1)

    result = []

    for label, color, engine, engine_key, line_type in seq:
        if engine in log_map:
            result.append((label, color, log_map[engine], engine_key, line_type))

    return result, program, dataset, int(workers)


def plot_run(files, args):
    (
        metrics,
        intervals,
        pretty,
        fullscreen,
        memclips,
        timeclips,
        skip_engines,
        no_legend,
        font_sizes,
    ) = (
        args.metrics,
        args.interval,
        not args.raw,
        args.fullscreen,
        args.memclip,
        args.timeclip,
        args.skip,
        args.nolegend,
        args.fontsizes,
    )

    run_organizer = {}

    for file in files:
        features = re.split(r"[/_.]", file.name)

        if features[-1] == "log":
            bucket = "_".join(features[-5:-2])

            if bucket in run_organizer:
                run_organizer[bucket].append(file)
            else:
                run_organizer[bucket] = [file]

    font_label, font_tick, font_legend = font_sizes

    run_cnt = len(run_organizer)
    chart_cnt = len(metrics)
    fig, run_graphs = plt.subplots(chart_cnt, run_cnt, figsize=(10, 10))

    if chart_cnt == 1:
        run_graphs = [run_graphs]

    if run_cnt == 1:
        run_graphs = [[ax] for ax in run_graphs]

    # Transpose to one run's chart per row
    run_graphs = [[run_graphs[j][i] for j in range(chart_cnt)] for i in range(run_cnt)]

    run_id = -1

    for group, graph_ax in zip(run_organizer, run_graphs):
        run_id += 1
        log_files = run_organizer[group]
        runs, program, dataset, workers = None, None, None, None

        if pretty:
            runs, program, dataset, workers = pretty_parse(log_files)
        else:
            colors = ["b", "g", "r", "c", "m", "y", "k", "orange", "purple", "brown"]
            runs = [
                (file.name, color, file, None, "-")
                for file, color in zip(log_files, colors)
            ]

        graph_lines = [[] for _ in range(chart_cnt)]
        priority = len(log_files)

        for label, clr, file, engine_key, line_type in runs:
            if pretty and skip_engines is not None and engine_key in skip_engines:
                continue

            data = pd.read_csv(file)

            # Cleanup data
            interval = -1

            if intervals is not None:
                if len(intervals) == 1:
                    interval = intervals[0]
                elif len(intervals) == run_cnt:
                    interval = intervals[run_id]
                else:
                    print("[error] specify interval for all graphs, once, or never.")
                    exit(1)

            if interval is not None and interval > 0:
                data["Time"] = (data["Time"] // interval) * interval
                df_resampled = data.groupby("Time", as_index=False).median()
                data = df_resampled

            timeclip = -1

            if timeclips is not None:
                if len(timeclips) == 1:
                    timeclip = timeclips[0]
                elif len(timeclips) == run_cnt:
                    timeclip = timeclips[run_id]
                else:
                    print("[error] specify timeclip for all graphs, once, or never.")
                    exit(1)

            if timeclip > 0:
                data = data[data["Time"] <= timeclip].copy()

            data["MEM Usage"] = data["MEM Usage"].div(1024.0 * 1024.0 * 1024.0)

            if pretty:
                data["CPU Percent"] = (
                    data["CPU Percent"].div(workers).clip(lower=0, upper=100)
                )

            memclip = -1

            if memclips is not None:
                if len(memclips) == 1:
                    memclip = memclips[0]
                elif len(memclips) == run_cnt:
                    memclip = memclips[run_id]
                else:
                    print("[error] specify memclip for all graphs, once, or never.")
                    exit(1)

            if memclip > 0:
                data["MEM Usage"] = data["MEM Usage"].clip(lower=0, upper=memclip)

            i = 0

            for g, ax in zip(metrics, graph_ax):
                if g == "c":
                    (line,) = ax.plot(
                        data["Time"],
                        data["CPU Percent"],
                        label=label,
                        linestyle=line_type,
                        color=clr,
                        zorder=priority,
                        linewidth=3,
                    )
                elif g == "m":
                    (line,) = ax.plot(
                        data["Time"],
                        data["MEM Usage"],
                        label=label,
                        linestyle=line_type,
                        color=clr,
                        zorder=priority,
                        linewidth=3,
                    )
                elif g == "r":
                    (line,) = ax.plot(
                        data["Time"],
                        data["IO Reads"] / 1024.0 / 1024.0,
                        label=label,
                        linestyle=line_type,
                        color=clr,
                        zorder=priority,
                        linewidth=3,
                    )

                graph_lines[i].append(line)
                i += 1

            priority -= 1

        graph_ax[-1].set_xlabel("Time (s)", fontsize=font_label, labelpad=10)

        for ax in graph_ax:
            ax.tick_params(axis="both", labelsize=font_tick)
            ax.grid()

    for g, ax in zip(metrics, run_graphs[0]):
        if g == "c":
            if not pretty:
                ax.set_title(
                    f"CPU Utilization for {program} ({dataset}) with {workers} threads"
                )
            ax.set_ylabel("CPU Usage (Percent)", fontsize=font_label, labelpad=10)
        elif g == "m":
            if not pretty:
                ax.set_title(
                    f"Memory Utilization for {program} ({dataset}) with {workers} threads"
                )
            ax.set_ylabel("Memory Usage (GiB)", fontsize=font_label, labelpad=10)
        elif g == "r":
            if pretty:
                ax.set_title(
                    f"Disk Reads for {program} ({dataset}) with {workers} threads"
                )
            ax.set_ylabel("Disk Reads (MiB)", fontsize=font_label, labelpad=10)

    if not no_legend:
        ax = run_graphs[0][0]
        handles, labels = ax.get_legend_handles_labels()
        ax = run_graphs[-1][-1]
        ax.legend(handles=handles, labels=labels, fontsize=font_legend)

        # handles, labels = ax.get_legend_handles_labels()
        # fig.legend(
        #     handles,
        #     labels,
        #     fontsize=font_legend,
        #     loc="lower center",
        #     ncol=5,
        #     bbox_to_anchor=(0.5, 0.01),
        # )

        #     fig.tight_layout(rect=[0, 0.1, 1, 1], pad=0.5)
        # else:
        plt.tight_layout()

    if pretty and run_cnt == 1:
        fig.canvas.manager.set_window_title(
            f"{program} {dataset} {workers} ({metrics})"
        )
    else:
        fig.canvas.manager.set_window_title("DlBench")

    manager = plt.get_current_fig_manager()
    manager.full_screen_toggle()

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
