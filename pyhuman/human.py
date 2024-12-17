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


TASK_CLUSTER_COUNT = 5
TASK_INTERVAL_SECONDS = 10
GROUPING_INTERVAL_SECONDS = 500
HUMAN_LIFESPAN_SECONDS = 0
EXTRA_DEFAULTS = []


def emulation_loop(workflows, clustersize, taskinterval, taskgroupinterval, lifespan_seconds, extra):
    t_end = time.time() + lifespan_seconds
    while True:
        for c in range(clustersize):
            err = None
            sleep(random.randrange(taskinterval))
            index = random.randrange(len(workflows))
            print(workflows[index].display)
            try:
                workflows[index].log_workflow_start()
                err = workflows[index].action(extra)
                if err:
                    workflows[index].log_workflow_error()
                else:
                    workflows[index].log_workflow_success()
            except KeyboardInterrupt:
                print('Keyboard interrupt detected, shutting down')
                return
            except:
                err = True
                workflows[index].log_workflow_error(message="Workflow {0} failed".format(workflows[index].display))
                print('')
                print("Workflow {0} failed".format(workflows[index].display))
                print(traceback.format_exc())
                print("Trying browser restart")
                WebDriverHelper().stop_browser()

            if not lifespan_seconds == 0 and time.time() >= t_end:
                if err is None:
                    # todo: last step (if any) should be marked as success too
                    workflows[index].log_workflow_success()
                    print("Finishing workflows due to time out")
                return

        sleep(random.randrange(taskgroupinterval))


def import_workflows():
    extensions = []
    for root, dirs, files in os.walk(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'app', 'workflows')):
        files = [f for f in files if not f[0] == '.' and not f[0] == "_"]
        dirs[:] = [d for d in dirs if not d[0] == '.' and not d[0] == "_"]
        for file in files:
            try:
                extensions.append(load_module('app/workflows', file))
            except Exception as e:
                print('Error could not load workflow. {}'.format(e))
    return extensions


def load_module(root, file):
    module = os.path.join(*root.split('/'), file.split('.')[0]).replace(os.path.sep, '.')
    workflow_module = import_module(module)
    return getattr(workflow_module, 'load')()


def run(clustersize, taskinterval, taskgroupinterval, lifespan_seconds, extra):
    workflows = import_workflows()

    def signal_handler(sig, frame):
        for workflow in workflows:
            workflow.cleanup()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    emulation_loop(workflows=workflows, clustersize=clustersize, taskinterval=taskinterval,
                    taskgroupinterval=taskgroupinterval, lifespan_seconds=lifespan_seconds, extra=extra)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Emulate human behavior on a system')
    parser.add_argument('--clustersize', type=int, default=TASK_CLUSTER_COUNT)
    parser.add_argument('--taskinterval', type=int, default=TASK_INTERVAL_SECONDS)
    parser.add_argument('--taskgroupinterval', type=int, default=GROUPING_INTERVAL_SECONDS)
    parser.add_argument('--stopafter', type=int, default=HUMAN_LIFESPAN_SECONDS)
    parser.add_argument('--extra', nargs='*', default=EXTRA_DEFAULTS)
    parser.add_argument('--seed', type=int, default=None)
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
            extra=args.extra
        )
    except KeyboardInterrupt:
        print(" Terminating human execution...")
        sys.exit()
