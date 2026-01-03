#!/usr/bin/env python3
import argparse
import sys
import subprocess
import os


def run_telemetry():
    subprocess.run(
        [sys.executable, os.path.join("astraguard", "telemetry", "telemetry_stream.py")]
    )


def run_dashboard():
    subprocess.run(["streamlit", "run", os.path.join("dashboard", "app.py")])


def run_simulation():
    subprocess.run([sys.executable, os.path.join("simulation", "attitude_3d.py")])


def run_classifier():
    subprocess.run([sys.executable, os.path.join("classifier", "fault_classifier.py")])


def run_logs(args):
    cmd = [sys.executable, os.path.join("logs", "timeline.py")]
    if args.export:
        cmd.extend(["--export", args.export])
    subprocess.run(cmd)


def run_api(args):
    cmd = [sys.executable, "run_api.py"]
    if args.host:
        cmd.extend(["--host", args.host])
    if args.port:
        cmd.extend(["--port", str(args.port)])
    if args.reload:
        cmd.append("--reload")
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(
        description="AstraGuard-AI: Unified CLI\nUse `cli.py <subcommand>`"
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("telemetry", help="Run telemetry stream generator")
    subparsers.add_parser("dashboard", help="Run Streamlit dashboard UI")
    subparsers.add_parser("simulate", help="Run 3D attitude simulation")
    subparsers.add_parser("classify", help="Run fault classifier tests")
    logs_parser = subparsers.add_parser("logs", help="Event log utilities")
    logs_parser.add_argument(
        "--export",
        metavar="PATH",
        help="Export event log to file (same as logs/timeline.py)",
    )

    api_parser = subparsers.add_parser("api", help="Run REST API server")
    api_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    api_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    api_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )

    args = parser.parse_args()
    if args.command == "telemetry":
        run_telemetry()
    elif args.command == "dashboard":
        run_dashboard()
    elif args.command == "simulate":
        run_simulation()
    elif args.command == "classify":
        run_classifier()
    elif args.command == "logs":
        run_logs(args)
    elif args.command == "api":
        run_api(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
