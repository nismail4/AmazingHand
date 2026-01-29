#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys
import atexit
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMP_CALIBRATION_FILE = BASE_DIR / "HandTracking/HandTracking/current_calibration.json"


def cleanup() -> None:
    if TEMP_CALIBRATION_FILE.exists():
        try:
            TEMP_CALIBRATION_FILE.unlink()
            print(f"[CLEANUP] Removed {TEMP_CALIBRATION_FILE}", flush=True)
        except Exception as e:
            print(
                f"[CLEANUP][WARNING] Failed to remove {TEMP_CALIBRATION_FILE}: {e}",
                file=sys.stderr,
            )


def handle_signal(signum, frame) -> None:
    print(f"\n[INFO] Received signal {signum}, shutting down...", flush=True)
    cleanup()
    sys.exit(130)


def run(
    cmd: list[str], env: dict[str, str] | None = None, cwd: Path | None = None
) -> None:
    print(f"\n>>> Running: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True, env=env, cwd=str(cwd) if cwd else None)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--IP_LAPTOP", required=True)
    parser.add_argument("--USER", default=None)
    args = parser.parse_args()

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    cleanup()  # start clean

    # Calibration step: run from BASE_DIR to be consistent
    if not args.USER or not args.USER.strip():
        run([sys.executable, "HandTracking/HandTracking/calibrate.py"], cwd=BASE_DIR)
    else:
        run(
            [
                sys.executable,
                "HandTracking/HandTracking/use_existing_calibration.py",
                "--user",
                args.USER,
                "--out",
                str(TEMP_CALIBRATION_FILE),
            ],
            cwd=BASE_DIR,
        )

    # Hard check
    if not TEMP_CALIBRATION_FILE.exists():
        print(
            f"[ERROR] Expected calibration file not found: {TEMP_CALIBRATION_FILE}",
            file=sys.stderr,
        )
        sys.exit(3)

    # Start Dora with debug logs + pass absolute path to all nodes
    env = os.environ.copy()
    env["RUST_LOG"] = "debug"
    env["CURRENT_CALIBRATION_FILE"] = str(TEMP_CALIBRATION_FILE)

    run(
        [
            "dora",
            "start",
            "--coordinator-addr",
            args.IP_LAPTOP,
            "dataflow_tracking_real_2hands_distributed.yml",
            "--uv",
        ],
        env=env,
        cwd=BASE_DIR,
    )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
