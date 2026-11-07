#!/usr/bin/env python3
"""Upload one file to BaiduPCS-Go and fall back when sustained throughput is low."""

from __future__ import annotations

import argparse
import os
import queue
import re
import subprocess
import sys
import threading
import time

SIZE_RE = re.compile(
    r"↑\s*([0-9]+(?:\.[0-9]+)?\s*(?:B|KB|MB|GB|TB|PB))\s*/",
    re.IGNORECASE,
)
SIZE_PART_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(B|KB|MB|GB|TB|PB)\s*$", re.I)
UNITS = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4, "PB": 1024**5}

CHECK_INTERVAL = 10 * 60
STARTUP_GRACE = 2 * 60
MINIMUM_BYTES_PER_SECOND = 2 * 1024 * 1024


def parse_size(value: str) -> int | None:
    match = SIZE_PART_RE.match(value)
    if not match:
        return None
    return int(float(match.group(1)) * UNITS[match.group(2).upper()])


def read_output(process: subprocess.Popen[str], output_queue: queue.Queue[str | None]) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        output_queue.put(line)
    output_queue.put(None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--remote-dir", required=True)
    parser.add_argument("--policy", default="overwrite")
    args = parser.parse_args()

    if not os.path.isfile(args.target):
        print(f"::error::Upload target does not exist: {args.target}", flush=True)
        return 1

    command = [
        args.binary,
        "upload",
        "--policy",
        args.policy,
        args.target,
        args.remote_dir,
    ]
    print("Starting monitored Baidu upload:", " ".join(command), flush=True)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        bufsize=1,
    )
    output_queue: queue.Queue[str | None] = queue.Queue()
    reader = threading.Thread(
        target=read_output, args=(process, output_queue), daemon=True
    )
    reader.start()

    latest_uploaded: int | None = None
    transfer_started_at: float | None = None
    baseline_bytes: int | None = None
    baseline_at: float | None = None
    output_closed = False

    try:
        while True:
            now = time.monotonic()
            try:
                line = output_queue.get(timeout=1)
                if line is None:
                    output_closed = True
                else:
                    print(line, end="", flush=True)
                    match = SIZE_RE.search(line)
                    if match:
                        uploaded = parse_size(match.group(1))
                        if uploaded is not None:
                            latest_uploaded = uploaded
                            if transfer_started_at is None:
                                transfer_started_at = now
                                print(
                                    "[upload-monitor] First transfer progress detected; "
                                    "starting 2-minute startup grace period.",
                                    flush=True,
                                )
            except queue.Empty:
                pass

            return_code = process.poll()
            if return_code is not None:
                # Drain any final output before evaluating the process result.
                while True:
                    try:
                        line = output_queue.get_nowait()
                    except queue.Empty:
                        break
                    if line is None:
                        output_closed = True
                    else:
                        print(line, end="", flush=True)
                        match = SIZE_RE.search(line)
                        if match:
                            uploaded = parse_size(match.group(1))
                            if uploaded is not None:
                                latest_uploaded = uploaded
                if return_code == 0:
                    print("[upload-monitor] Baidu upload completed successfully.", flush=True)
                    return 0
                print(
                    f"::error::BaiduPCS-Go upload exited with code {return_code}.",
                    flush=True,
                )
                return return_code if return_code > 0 else 1

            if transfer_started_at is None or latest_uploaded is None:
                continue

            if baseline_at is None:
                if now - transfer_started_at >= STARTUP_GRACE:
                    baseline_bytes = latest_uploaded
                    baseline_at = now
                    print(
                        "[upload-monitor] Startup grace finished. "
                        "Beginning 10-minute throughput checks.",
                        flush=True,
                    )
                continue

            elapsed = now - baseline_at
            if elapsed >= CHECK_INTERVAL:
                uploaded_delta = max(0, latest_uploaded - (baseline_bytes or 0))
                average_speed = uploaded_delta / elapsed
                print(
                    "[upload-monitor] Last interval: "
                    f"{uploaded_delta / (1024 * 1024):.2f} MiB in "
                    f"{elapsed / 60:.1f} min; average "
                    f"{average_speed / (1024 * 1024):.2f} MiB/s "
                    f"(minimum 2.00 MiB/s).",
                    flush=True,
                )
                if average_speed < MINIMUM_BYTES_PER_SECOND:
                    print(
                        "::warning::Baidu upload throughput is below 2 MiB/s. "
                        "Stopping Baidu upload and falling back to GitHub Artifact.",
                        flush=True,
                    )
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    return 10

                baseline_bytes = latest_uploaded
                baseline_at = now

    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
