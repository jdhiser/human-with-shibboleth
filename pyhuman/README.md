# Human Workflow Emulator

This project simulates human-like behavior by executing randomized workflows in a clustered fashion. Each workflow is defined in the `app/workflows/` directory and is dynamically loaded at runtime.

## Features

* Dynamic discovery and loading of workflow modules
* Configurable task cluster size and timing
* Optional time-limited execution
* Optional filtering of specific workflows to run
* Graceful shutdown and cleanup on signals
* Compatibility with both `BaseWorkflow` and `MetricWorkflow` types

## Requirements

* Python 3.10+
* Workflow modules must define a `load()` function that returns an object with the following members:

  * `display` (str): A string used for identifying the workflow
  * `action(extra)`: Main logic of the workflow; returns truthy on error
  * `cleanup()`: Cleanup function called during shutdown 

## Usage

```bash
python3 human.py [options]
```

### Options

* `--clustersize`: Number of workflows to run per iteration (default: 5)
* `--taskinterval`: Max random interval between individual task starts (default: 10 seconds)
* `--taskgroupinterval`: Max random interval between task groups (default: 500 seconds)
* `--stopafter`: Number of seconds before stopping the emulator (default: 0 = run indefinitely)
* `--extra`: Extra arguments passed to each workflow (default: empty list)
* `--seed`: Seed for the random number generator (default: None)
* `--workflows`: List of specific workflow module names (without `.py`) to load (default: load all)

### Example

```bash
python3 human.py --clustersize 3 --taskinterval 5 --workflows login browse checkout
```

This example loads and randomly executes only the `login`, `browse`, and `checkout` workflows, running up to 3 in parallel.

## Adding a Workflow

1. Create a new file in `app/workflows/` (e.g., `myworkflow.py`).
2. Implement a `load()` function that returns an object with at least the `BaseWorkflow` interface (`display`, `action`, `cleanup`).
3. Subclass `BaseWorkflow` or `MetricWorkflow` to enable logging metrics.


