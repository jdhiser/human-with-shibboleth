import argparse
import signal
import os
import random
import sys
from importlib import import_module
from time import sleep
import traceback
import time
from app.utility.webdriver_helper import WebDriverHelper
from app.utility.metric_workflow import MetricWorkflow  # Import to use isinstance


# Constants for default values
TASK_CLUSTER_COUNT = 5
TASK_INTERVAL_SECONDS = 10
GROUPING_INTERVAL_SECONDS = 500
HUMAN_LIFESPAN_SECONDS = 0
EXTRA_DEFAULTS = []


def handle_workflow(workflow, extra):
    """
    handle_workflow

    Executes a single workflow action with appropriate logging and error handling.

    Parameters:
    workflow (object): The workflow instance.
    extra (list): Extra arguments for the workflow.

    Return:
    bool: True if the action failed, False otherwise.
    """
    err = False
    try:
        if isinstance(workflow, MetricWorkflow):
            workflow.log_workflow_start()

        result = workflow.action(extra)
        err = bool(result)

        if isinstance(workflow, MetricWorkflow):
            if err:
                workflow.log_workflow_error()
            else:
                workflow.log_workflow_success()

    except KeyboardInterrupt:
        raise

    except Exception:
        err = True
        if isinstance(workflow, MetricWorkflow):
            workflow.log_workflow_error(message=f"Workflow {workflow.display} failed")
        print(f"\nWorkflow {workflow.display} failed")
        print(traceback.format_exc())
        print("Trying browser restart")
        WebDriverHelper().stop_browser()

    return err


def emulation_loop(workflows: list, clustersize: int, taskinterval: int, taskgroupinterval: int,
                   lifespan_seconds: int, extra: list) -> None:
    """
    emulation_loop

    Parameters:
    workflows (list): List of workflow instances.
    clustersize (int): Number of tasks to run concurrently.
    taskinterval (int): Max interval between individual task executions.
    taskgroupinterval (int): Max interval between task groups.
    lifespan_seconds (int): Duration to run the loop.
    extra (list): Extra parameters for workflows.

    Return:
    None
    """
    infinite = lifespan_seconds == 0
    t_end = time.time() + lifespan_seconds

    while infinite or time.time() < t_end:
        for _ in range(clustersize):
            sleep(random.randrange(taskinterval))
            workflow = random.choice(workflows)
            print(workflow.display)

            try:
                err = handle_workflow(workflow, extra)
            except KeyboardInterrupt:
                print('Keyboard interrupt detected, shutting down')
                return

            if not infinite and time.time() >= t_end:
                if not err and isinstance(workflow, MetricWorkflow):
                    workflow.log_workflow_success()
                    print("Finishing workflows due to time out")
                return

        sleep(random.randrange(taskgroupinterval))


def import_workflows(selected_workflows: list | None = None) -> list:
    """
    import_workflows

    Parameters:
    selected_workflows (list|None): List of workflow names to import, or None to import all.

    Return:
    list: List of loaded workflow instances.
    """
    extensions = []
    root_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'app', 'workflows')

    for root, dirs, files in os.walk(root_dir):
        files = [f for f in files if not f.startswith(('.', '_'))]
        dirs[:] = [d for d in dirs if not d.startswith(('.', '_'))]

        for file in files:
            name = os.path.splitext(file)[0]
            if selected_workflows and name not in selected_workflows:
                continue

            try:
                extensions.append(load_module('app/workflows', file))
            except Exception as e:
                print(f'Error could not load workflow {file}: {e}')

    return extensions


def load_module(root: str, file: str):
    """
    load_module

    Parameters:
    root (str): Root Python module path.
    file (str): Filename of the workflow script.

    Return:
    object: The result of the workflow module's load() function.
    """
    module = os.path.join(*root.split('/'), file.split('.')[0]).replace(os.path.sep, '.')
    workflow_module = import_module(module)
    return getattr(workflow_module, 'load')()


def run(clustersize: int, taskinterval: int, taskgroupinterval: int,
        lifespan_seconds: int, extra: list, workflows_list: list | None = None) -> None:
    """
    run

    Parameters:
    clustersize (int): Number of tasks to run concurrently.
    taskinterval (int): Max interval between individual task executions.
    taskgroupinterval (int): Max interval between task groups.
    lifespan_seconds (int): Duration to run the loop.
    extra (list): Extra parameters for workflows.
    workflows_list (list|None): Specific workflows to load.

    Return:
    None
    """
    workflows = import_workflows(workflows_list)

    def signal_handler(sig, frame):
        for workflow in workflows:
            workflow.cleanup()
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    emulation_loop(workflows=workflows, clustersize=clustersize, taskinterval=taskinterval,
                   taskgroupinterval=taskgroupinterval, lifespan_seconds=lifespan_seconds, extra=extra)


def main() -> None:
    """
    main

    Entry point of the script. Parses command-line arguments and invokes the run function.

    Return:
    None
    """
    parser = argparse.ArgumentParser(description='Emulate human behavior on a system')
    parser.add_argument('--clustersize', type=int, default=TASK_CLUSTER_COUNT)
    parser.add_argument('--taskinterval', type=int, default=TASK_INTERVAL_SECONDS)
    parser.add_argument('--taskgroupinterval', type=int, default=GROUPING_INTERVAL_SECONDS)
    parser.add_argument('--stopafter', type=int, default=HUMAN_LIFESPAN_SECONDS)
    parser.add_argument('--extra', nargs='*', default=EXTRA_DEFAULTS)
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--workflows', nargs='*', help='Names of specific workflows to load (without .py)')

    args = parser.parse_args()

    try:
        if args.seed is not None:
            random.seed(args.seed)
        else:
            random.seed()

        run(
            clustersize=args.clustersize,
            taskinterval=args.taskinterval,
            taskgroupinterval=args.taskgroupinterval,
            lifespan_seconds=args.stopafter,
            extra=args.extra,
            workflows_list=args.workflows
        )

    except KeyboardInterrupt:
        print(" Terminating human execution...")
        sys.exit()


if __name__ == '__main__':
    main()

