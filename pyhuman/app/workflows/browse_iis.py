from time import sleep
import random
import ssl
import socket

from ..utility.metric_workflow import MetricWorkflow
from ..utility.webdriver_helper import WebDriverHelper
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

WORKFLOW_NAME = 'IISBrowser'
WORKFLOW_DESCRIPTION = 'Browse a website secured ADCS'

DEFAULT_INPUT_WAIT_TIME = 2
# Minimum amount of time to wait after searching, in seconds
MIN_WAIT_TIME = 2
# Maximum amount of time to wait after searching, in seconds
MAX_WAIT_TIME = 5


def load():
    """
    Load the IIS workflow with an initialized WebDriver.

    Returns:
        IISBrowse: Instance of the workflow.
    """
    driver = WebDriverHelper()
    return IISBrowse(driver=driver)


def check_cert_trust_new(hostname: str, port: int = 443) -> bool:
    """
    Check if the server's certificate is trusted using your custom CA bundle.

    Args:
        hostname (str): Hostname to check.
        port (int): Port to connect to (default 443).

    Returns:
        bool: True if the certificate is trusted, False otherwise.
    """
    ca_bundle_path = "/tmp/castle-ca-bundle.pem"  # update this to match your location

    try:
        context = ssl.create_default_context(cafile=ca_bundle_path)
        with socket.create_connection((hostname, port)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                print(f"... TLS certificate subject: {cert.get('subject')}")
        return True
    except ssl.SSLCertVerificationError as e:
        print(f"... Certificate verification failed: {e}")
        return False
    except Exception as e:
        print(f"... Unexpected error checking certificate: {e}")
        return False


def check_cert_trust_old(hostname: str, port: int = 443) -> bool:
    """
    Check if the server's certificate is trusted using system CAs.

    Args:
        hostname (str): Hostname to check.
        port (int): Port to connect to (default 443).

    Returns:
        bool: True if the certificate is trusted, False otherwise.
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                print(f"... TLS certificate subject: {cert.get('subject')}")
        return True
    except ssl.SSLCertVerificationError as e:
        print(f"... Certificate verification failed: {e}")
        return False
    except Exception as e:
        print(f"... Unexpected error checking certificate: {e}")
        return False


def check_cert_trust(hostname: str, port: int = 443) -> bool:
        return check_cert_trust_old(hostname,port);


class IISBrowse(MetricWorkflow):
    """
    Workflow for browsing a Shibboleth-secured website.

    Automates login and logout, logs each step, and checks whether the secure page loads.
    """

    def __init__(self, driver, input_wait_time=DEFAULT_INPUT_WAIT_TIME):
        """
        Initialize workflow state.

        Args:
            driver (WebDriverHelper): WebDriver abstraction.
            input_wait_time (int): Seconds to wait before interaction steps.
        """
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION, driver=driver)

    def action(self, extra=None):
        """
        Main entry point for the workflow.

        Args:
            extra (list, optional): Optional extra arguments for credential loading.

        Returns:
            bool: True on error, False on success.
        """
        return self.load_iis_webpage()


    def load_iis_webpage(self) -> bool:
        """
        Attempt to sign into an IIS service.

        Returns:
            bool: True if an error occurred during loading/verification
        """
        err = True

        # Navigate to the secure service page
        self.driver.driver.get('https://iis.castle.project1.os/')
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        # Attempt to locate the secured content on the post-login page
        print("... Checking that page loaded with certificate ")

        page_integrity = self.check_integrity()

        # Check if the certificate is trusted using socket/ssl
        cert_trusted = check_cert_trust("iis.castle.project1.os")
        print(f"... Certificate trusted: {cert_trusted}")

        search_element = self.driver.driver.find_element(By.XPATH, '/html/body/p')
        if search_element is None:
            print("Could not find body paragraph of secured page")
            self.log_step_error("page-loaded",
                                integrity=page_integrity)
            return err

        # Determine success of login based on expected text
        if 'This site is secured with a certificate from Active Directory Certificate Services.' in search_element.text:
            print(f"... Page load successful!")
            err = False
            # Log login result including integrity status
            self.log_step_success("page-loaded",
                                  integrity=page_integrity)
        else:
            print(f"... Login failed with: {search_element.text}")
            self.log_step_error("page-loaded",
                                integrity=page_integrity)

        return err

