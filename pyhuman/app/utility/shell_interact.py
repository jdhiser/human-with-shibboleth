import os
import pty
import time
import select
import threading
import re
import sys
import random
import difflib
from typing import Callable, List, Literal, TypedDict

# Result type returned by the sanity check callback
SanityCheckResult = Literal["success", "retry", "fail"]

# CommandTask defines the structure for each command object


class CommandTask(TypedDict):
    command: str
    check: Callable[["CommandTask", str, int], SanityCheckResult]

# Run commands using the provided HumanTyperShell instance, retrying as instructed by the check callback.
# Throws RuntimeError if a task ultimately fails.
def run_shell_commands_with_checks(
    shell,
    tasks: List[CommandTask],
    max_retries: int = 3,
    step_logger = None
):
    """
    Executes a series of shell commands with retry logic and optional step logging.

    Parameters:
    shell: An object with a type_command(str) -> str method for running shell commands.
    tasks: A list of CommandTask dicts, each containing a 'command' string and a 'check' function.
    max_retries: Maximum number of retries for each command on transient failure.
    step_logger: Optional object with logging methods log_step_start, log_step_success, log_step_error,
                 and check_external_integrity(output) for recording progress and results.

    Raises:
    RuntimeError if a command fails permanently or exceeds retry limit.
    """

    def _log_if_present(method_name: str, *args, **kwargs):
        # Invoke a logging method on the logger if it exists
        if step_logger:
            log_fn = getattr(step_logger, method_name, None)
            if callable(log_fn):
                log_fn(*args, **kwargs)

    def _synthesize_step_name(command: str, index: int) -> str:
        # Replace non-alphanumeric characters with underscores, normalize, and prefix with task index
        name = re.sub(r'_+', '_', re.sub(r'[^a-zA-Z0-9]', '_', command)).strip('_')
        name = name[:32]  # leave space for prefix
        return f"{index:02d}_{name}"

    def _execute_task_with_retries(task, step_name):
        # Run a single task with retries and logging
        fail_count = 0
        while fail_count <= max_retries:
            output = shell.type_command(task["command"])
            result = task["check"](task, output, fail_count)
            integrity = step_logger.check_external_integrity(output) if step_logger else None

            if result == "success":
                _log_if_present("log_step_success", step_name, integrity=integrity)
                return

            if result == "retry":
                fail_count += 1
                continue

            # Permanent failure
            _log_if_present("log_step_error", step_name, integrity=integrity)
            raise RuntimeError(
                f"Command permanently failed: {task['command']}\nOutput:\n{output}"
            )

        # Exceeded retry limit
        integrity = step_logger.check_integrity(output) if step_logger else True
        _log_if_present("log_step_error", step_name, integrity=integrity)
        raise RuntimeError(
            f"Command failed after {max_retries} retries: {task['command']}\nLast output:\n{output}"
        )

    # Execute each task in order, logging progress and handling failures
    for index, task in enumerate(tasks):
        step_name = _synthesize_step_name(task["command"], index)
        _log_if_present("log_step_start", step_name, message=task['command'])
        _execute_task_with_retries(task, step_name)


# Example usage
if __name__ == "__main__":
    from human_typer import HumanTyperShell  # Updated import to match file name

    def jittery_typist():
        return random.gauss(0.1, 0.03)

    def check_exact_string(task, output, fail_count):
        print("[DEBUG] Checking for line containing: 'bob likes ponies'")
        expected = "bob likes ponies"
        lines = [line.strip()
                 for line in output.strip().splitlines() if line.strip()]
        for line in lines:
            if expected in line:
                return "success"
        return "retry" if fail_count < 2 else "fail"

    shell = HumanTyperShell(
        live_echo=True, keystroke_delay_fn=jittery_typist, verbose=True)
    try:
        run_shell_commands_with_checks(
            shell=shell,
            tasks=[
                {
                    "command": "ls -l /etc/passwd",
                    "check": lambda task, output, fail_count: (
                        "retry" if "No such file" in output and fail_count < 2 else
                        "fail" if "No such file" in output or task["command"].split()[-1] not in output else
                        "success"
                    )
                },
                {
                    "command": "echo bob likes ponies",
                    "check": check_exact_string
                }
            ]
        )
    finally:
        shell.close()
