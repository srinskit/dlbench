import argparse
from . import bench
import time


def main():
    parser = argparse.ArgumentParser(description="A benchmark tool for Datalog engines")

    subparsers = parser.add_subparsers(dest="mode", required=True)

    p1 = subparsers.add_parser("run", help="Run the benchmark for an engine")

    p1.add_argument(
        "cmd", type=str, help="Shell command that would execute the benchmark target"
    )

    p1.add_argument("tag", type=str, help="Name to tag the results with")

    p1.add_argument(
        "suffix-time", action="store_true", help="Suffix the tag with a timestamp"
    )

    p1.add_argument(
        "--monitor",
        "-m",
        nargs="+",
        type=str,
        help="Names of systemd processes to monitor in addition to benchmark target",
    )

    p2 = subparsers.add_parser("plot", help="Plot stats from previous runs")
    p2.add_argument("--pretty", "-p", action="store_true", help="Denoise and plot")
    group = p2.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--logs",
        type=argparse.FileType("r"),
        help="Path to log files of runs",
        nargs="+",
    )

    group.add_argument("--last", type=int, help="Plot recent runs")

    # TODO allow choosing of dir for last

    # TODO add clean option

    args = parser.parse_args()

    if args.mode == "run":
        tag = args.tag

        if args.suffix_time:
            local_time = time.localtime()
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", local_time)
            tag = tag + "_" + timestamp

        print("Run name:", tag)
        f = open(tag + ".out", "w")
        start_time = time.time()
        sh, target_process = bench.start_target(args.cmd, f)

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
        f.close()

    elif args.mode == "plot":
        if args.last is not None:
            runs = bench.find_latest_logs(".", args.last)

            if runs is None:
                print("Error: could not find logs")
            else:
                runs = [run[2:-4] for run in runs]
                print("Run names:", runs)
                bench.plot_run(runs, args)
        else:
            bench.plot_run([file.name[:-4] for file in args.logs], args)


if __name__ == "__main__":
    cli()
