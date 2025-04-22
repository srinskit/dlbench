import argparse
from . import bench
import time


def main():
    parser = argparse.ArgumentParser(
        description="A utility to monitor, plot and compare resource utilization of programs."
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    mode_run_args = subparsers.add_parser("run", help="Run the benchmark for an engine")

    mode_run_args.add_argument(
        "cmd", type=str, help="Shell command that would execute the benchmark target"
    )

    mode_run_args.add_argument("tag", type=str, help="Name to tag the results with")

    mode_run_args.add_argument(
        "--suffix-time", action="store_true", help="Suffix the tag with a timestamp"
    )

    mode_run_args.add_argument(
        "--monitor",
        metavar="process",
        nargs="+",
        type=str,
        help="Names of additional systemd processes to monitor",
    )

    mode_plot_args = subparsers.add_parser("plot", help="Plot logs from past runs")

    mode_plot_args.add_argument(
        "--interval",
        type=float,
        help="The resolution of the time axis in seconds",
    )
    mode_plot_args.add_argument(
        "--memclip",
        metavar="Memory Limit (GiB)",
        type=float,
        help="The maximum memory utilization to be shown",
    )
    mode_plot_args.add_argument(
        "--raw", action="store_true", help="Do not enhance label and plot order"
    )
    mode_plot_args.add_argument(
        "--fullscreen", action="store_true", help="Show plot in fullscreen window"
    )
    
    mode_plot_args.add_argument(
        "--nolegend", action="store_true", help="Do not show the legend"
    )

    mode_plot_args.add_argument(
        "--skip",
        metavar="acronym",
        type=str,
        help="Engines to skip (f: Flowlog, s: Souffle (compiled), i: Souffle (interpreted), r: RecStep, d: DDLog)",
    )

    mode_plot_args.add_argument(
        "--metrics",
        metavar="acronym",
        type=str,
        default="cm",
        help="Metrics to plot (c: CPU, m: memory, r: disk reads)",
    )
    
    mode_plot_args.add_argument(
        "--fontsizes",
        metavar="sizes",
        type=str,
        default="16,14,14",
        help="Comma-separated font sizes for the label, ticks, and legend",
    )

    group = mode_plot_args.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--logs",
        metavar="file",
        type=argparse.FileType("r"),
        help="Path to log files of runs",
        nargs="+",
    )

    group.add_argument("--last", metavar="count", type=int, help="Plot recent runs")

    args = parser.parse_args()

    if args.mode == "run":
        tag = args.tag

        if args.suffix_time:
            local_time = time.localtime()
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", local_time)
            tag = tag + "_" + timestamp

        print("Run name:", tag)

        output_file = open(tag + ".out", "w")
        start_time = time.time()
        sh, target_process = bench.start_target(args.cmd, output_file)

        if target_process is not None:
            try:
                bench.benchmark(tag, sh, target_process, start_time, args.monitor)
            except KeyboardInterrupt:
                print("Exiting benchmark")
            except Exception as e:
                print(f"An error occurred: {e}")
            finally:
                bench.cleanup()
        else:
            print("Error: could not find a process to monitor")

        sh.wait()
        output_file.close()
        exit(sh.returncode)

    elif args.mode == "plot":

        # Validate metrics to plot
        for ch in args.metrics:
            if ch not in ("c", "m", "r"):
                print(f"Error: invalid graph type '{ch}' in '{args.metrics}'.")
                exit(1)

        if args.last is not None:
            runs = bench.find_latest_logs(".", args.last)

            if runs is None:
                print("Error: could not find logs")
            else:
                print("Run names:", runs)
                bench.plot_run(runs, args)
        else:
            bench.plot_run(args.logs, args)


if __name__ == "__main__":
    cli()
