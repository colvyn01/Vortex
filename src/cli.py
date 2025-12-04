"""Command-line interface for Vortex file gateway."""

import argparse
import os
import signal
import sys
from pathlib import Path

from .server import run_server

DEFAULT_PORT = 8000
DEFAULT_DIR = "."
DEFAULT_MAX_PARALLEL = 4

# PID file location
def _get_pid_file() -> Path:
    """Get the path to the PID file."""
    if sys.platform == "win32":
        # Windows: use LOCALAPPDATA or temp
        app_data = os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", "."))
        return Path(app_data) / "vortex.pid"
    else:
        # Unix: use home directory
        return Path.home() / ".vortex.pid"


def _write_pid_file() -> None:
    """Write current process ID to PID file."""
    pid_file = _get_pid_file()
    try:
        pid_file.write_text(str(os.getpid()))
    except OSError:
        pass  # Non-critical if we can't write PID file


def _remove_pid_file() -> None:
    """Remove the PID file."""
    pid_file = _get_pid_file()
    try:
        pid_file.unlink(missing_ok=True)
    except OSError:
        pass


def _read_pid_file() -> int | None:
    """Read PID from file, return None if not found or invalid."""
    pid_file = _get_pid_file()
    try:
        if pid_file.exists():
            pid_str = pid_file.read_text().strip()
            return int(pid_str)
    except (OSError, ValueError):
        pass
    return None


def _is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    if sys.platform == "win32":
        # Windows: try to open the process
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        # Unix: send signal 0 to check if process exists
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _terminate_process(pid: int) -> bool:
    """Terminate a process by PID. Returns True if successful."""
    if sys.platform == "win32":
        # Windows: use taskkill
        import subprocess
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except OSError:
            return False
    else:
        # Unix: send SIGTERM
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except OSError:
            return False


def _create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="vortex",
        description="Vortex – fast, cross-platform file transfer over local Wi-Fi",
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Start the file gateway server",
    )
    parser.add_argument(
        "--deactivate",
        action="store_true",
        help="Stop a running Vortex server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--dir",
        default=DEFAULT_DIR,
        help="Directory to share (default: current directory)",
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=DEFAULT_MAX_PARALLEL,
        help=f"Max parallel uploads from browser (default: {DEFAULT_MAX_PARALLEL})",
    )
    return parser


def main() -> None:
    """Parse arguments and start/stop the server."""
    parser = _create_parser()
    args = parser.parse_args()

    # Handle --deactivate
    if args.deactivate:
        pid = _read_pid_file()
        if pid is None:
            print("No running Vortex server found.")
            return
        
        if not _is_process_running(pid):
            print(f"Vortex server (PID {pid}) is not running.")
            _remove_pid_file()
            return
        
        print(f"Stopping Vortex server (PID {pid})...")
        if _terminate_process(pid):
            _remove_pid_file()
            print("Vortex deactivated.")
        else:
            print("Failed to stop Vortex server.")
        return

    # Handle --activate
    if args.activate:
        # Check if already running
        existing_pid = _read_pid_file()
        if existing_pid and _is_process_running(existing_pid):
            print(f"Vortex is already running (PID {existing_pid}).")
            print("Use 'vortex --deactivate' to stop it first.")
            return
        
        # Write PID file and start server
        _write_pid_file()
        try:
            run_server(args.dir, args.port, args.max_parallel)
        finally:
            _remove_pid_file()
        return

    # No action specified
    parser.print_help()

