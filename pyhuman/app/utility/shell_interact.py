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
    max_retries: int = 3
):
    for task in tasks:
        fail_count = 0
        while True:
            output = shell.type_command(task["command"])
            result = task["check"](task, output, fail_count)
            if result == "success":
                break
            elif result == "retry":
                fail_count += 1
                if fail_count > max_retries:
                    raise RuntimeError(
                        f"Command failed after {max_retries} retries: {task['command']}\nLast output:\n{output}")
            else:
                raise RuntimeError(
                    f"Command permanently failed: {task['command']}\nOutput:\n{output}")


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
