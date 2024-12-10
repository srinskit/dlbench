import argparse
from . import bench

def main():
    parser = argparse.ArgumentParser(description="A benchmark tool for Datalog engines")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    p1 = subparsers.add_parser("run", help="Run the benchmark for an engine")
    p1.add_argument("cmd", type=str, help="Shell command that would execute the benchmark target")

    p2 = subparsers.add_parser("plot", help="Plot stats from previous runs")
    group = p2.add_mutually_exclusive_group(required=True)
    group.add_argument("--logs", type=argparse.FileType("r"), help="Path to log files of runs", nargs="+")
    group.add_argument("--last", type=int, help="Plot recent runs") 
    # TODO allow choosing of dir for last

    # TODO add clean option
    
    args = parser.parse_args()

    if args.mode == "run":
        bench.print_sys_metadata()
        sh, target_process = bench.start_target(args.cmd)
        run_name = bench.gen_run_name(target_process)
        print("Run name:", run_name)
        print("Logging stats to:", run_name + ".log")
        try:
            bench.benchmark(run_name, sh, target_process)
        except KeyboardInterrupt:
            print("Exiting benchmark")
        sh.wait()
    elif args.mode == "plot":
        if args.last is not None:
            runs = bench.find_latest_logs(".", args.last)
            
            if runs is None:
                print("Error: could not find logs")
            else:
                runs = [run[2:-4] for run in runs]
                print("Run names:", runs)
                bench.plot_run(runs)
        else:
            bench.plot_run([file.name[:-4] for file in args.logs])

if __name__ == "__main__":
    cli()