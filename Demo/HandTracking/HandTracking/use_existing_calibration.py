#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


DEFAULT_DB_PATH = Path("HandTracking/HandTracking/user_calibration.json")
DEFAULT_CURRENT_PATH = Path("HandTracking/HandTracking/current_calibration.json")


def die(msg: str, code: int = 1) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load an existing calibration for a user and write it to current_calibration.json"
    )
    parser.add_argument(
        "--user",
        "--USER",
        dest="user",
        required=True,
        help="User key in user_calibration.json",
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"Path to calibration database JSON (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_CURRENT_PATH),
        help=f"Output path for current calibration (default: {DEFAULT_CURRENT_PATH})",
    )
    args = parser.parse_args()

    user = args.user.strip()
    if not user:
        die("Empty --USER/--user provided.")

    db_path = Path(args.db)
    out_path = Path(args.out)

    if not db_path.exists():
        die(f"Calibration DB not found: {db_path}")

    # Read DB
    try:
        with db_path.open("r", encoding="utf-8") as f:
            db = json.load(f)
    except json.JSONDecodeError as e:
        die(f"Invalid JSON in {db_path}: {e}")
    except Exception as e:
        die(f"Failed to read {db_path}: {e}")

    if not isinstance(db, dict):
        die(
            f"Expected {db_path} to contain a JSON object (dict), got {type(db).__name__}."
        )

    if user not in db:
        available = ", ".join(sorted(db.keys())) if db else "(none)"
        die(
            f"User '{user}' not found in {db_path}. Available users: {available}",
            code=2,
        )

    calibration = db[user]

    # Write current calibration
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(calibration, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except Exception as e:
        die(f"Failed to write {out_path}: {e}")

    print(f"[OK] Loaded calibration for '{user}' from {db_path} -> {out_path}")


if __name__ == "__main__":
    main()
