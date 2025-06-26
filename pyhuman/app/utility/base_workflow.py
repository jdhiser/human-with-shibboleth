from abc import abstractmethod
import json
import logging
import os
import socket
from datetime import datetime

# Configure the logger
logging.basicConfig(level=logging.INFO, format='%(message)s')

def get_local_hostname():
    """Retrieve the local hostname."""
    try:
        hostname = socket.gethostname()
        return hostname
    except Exception as e:
        return f"Error retrieving hostname: {e}"


class BaseWorkflow(object):

    @property
    def display(self):
        return 'Running Task: {}'.format(self.description)

    __slots__ = ['name', 'description', 'driver']

    @abstractmethod
    def __init__(self, name, description, driver=None):
        self.name = name
        self.description = description
        self.driver = driver
        self.integrity = 1

    @abstractmethod
    def action(self, extra=None):
        pass
    
    def cleanup(self):
        if self.driver is None:
            return
        self.driver.cleanup()


    def _log(self, message, step_name, status, integrity):
        """
        Log a workflow or workflow step in JSON format.

        Parameters:
        - workflow_name (str): Name of the workflow.
        - message (str): A message describing the event.
        - status (str): Status of the step ("start", "success", "error").
        - step_name (str, optional): Name of the current step in the workflow (default: None).
        """
        if integrity is not None:
            self.integrity &= integrity
        valid_statuses = {"start", "success", "error"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: '{status}'. Valid statuses are {valid_statuses}.")
    
     
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "workflow_name": self.name,
            "status": status,
            "message": message,
            "hostname": get_local_hostname(),
            "pid": os.getpid(),
        }
        if integrity is not None:
            log_entry["integrity"] = integrity

        # Add step_name only if it's provided
        if step_name is not None:
            log_entry["step_name"] = step_name
    
        # Print out on a single line
        logging.info(json.dumps(log_entry))

        # print out as before
        if step_name:
            print(f"... {timestamp} {step_name}: {message}")
        else:
            print(f"{timestamp} {message}")

    # STEP
    def log_step_start(self, step_name, message=""):
        if not message:
            message=f"Starting step {step_name}"
        self._log(message, step_name, "start", integrity=None)
    
    def log_step_success(self, step_name, message="", integrity=None):
        if not message:
            message=f"Step {step_name} successful"
        self._log(message, step_name, "success", integrity)

    def log_step_error(self, step_name, message="", integrity=None):
        if not message:
            message=f"Step {step_name} failed"
        self._log(message, step_name, "error", integrity)

    # WORKFLOW
    def log_workflow_start(self, message=""):
        if not message:
            message=f"Starting workflow {self.name}: {self.description}"
        self._log(message, None, "start", integrity=None)
    
    def log_workflow_success(self, message=""):
        if not message:
            message=f"Workflow {self.name} was successful"
        self._log(message, None, "success", self.integrity)

    def log_workflow_error(self, message=""):
        if not message:
            message=f"Workflow {self.name} had an error"
        self._log(message, None, "error", self.integrity)

