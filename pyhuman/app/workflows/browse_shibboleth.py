from time import sleep
import random

# from soupsieve import select

from ..utility.metric_workflow import MetricWorkflow
from ..utility.webdriver_helper import WebDriverHelper
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

WORKFLOW_NAME = 'ShibbolethBrowser'
WORKFLOW_DESCRIPTION = 'Browse a website secured by Shibboleth'

DEFAULT_INPUT_WAIT_TIME = 2
# Minimum amount of time to wait after searching, in seconds
MIN_WAIT_TIME = 2
# Maximum amount of time to wait after searching, in seconds
MAX_WAIT_TIME = 5


def load():
    """
    Load the Shibboleth workflow with an initialized WebDriver.

    Returns:
        ShibbolethBrowse: Instance of the workflow.
    """
    driver = WebDriverHelper()
    return ShibbolethBrowse(driver=driver)


class ShibbolethBrowse(MetricWorkflow):
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
        self.username = None
        self.password = None

    def action(self, extra=None):
        """
        Main entry point for the workflow.

        If credentials are not yet loaded, calls get_creds(). Then attempts sign-in.

        Args:
            extra (list, optional): Optional extra arguments for credential loading.

        Returns:
            bool: True on error, False on success.
        """
        if self.username is None:
            self.get_creds(extra)
        err = self.sign_in()
        return err

    def get_creds(self, extra=None):
        """
        Load credentials either from hardcoded default or from a specified password file.

        Args:
            extra (list, optional): If ['passfile', <filename>] is passed, reads credentials from file.
        """
        self.username = 'jdh'
        self.password = 'jdhpass'

        passfile = None
        if len(extra) == 2:
            if extra[0] == "passfile":
                with open(extra[1]) as f:
                    self.username = f.readline().strip()
                    self.password = f.readline().strip()

    def sign_in(self) -> bool:
        """
        Attempt to sign into a Shibboleth-protected service using stored credentials.

        Navigates to the login page, fills in the username and password, and clicks the login button.
        Before any interaction, it checks the loaded HTML source for undesirable integrity markers.
        After logging in, it verifies that the secure page has loaded correctly.

        Returns:
            bool: True if an error occurred during login, False if login was successful.
        """
        err = True

        # Navigate to the secure service page
        self.driver.driver.get('https://service.project1.os/secure/index.html')
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        try:
            login_page_integrity = self.check_integrity()
            # Attempt to locate and fill in the username field
            print(f"... Trying to enter username '{self.username}'")
            search_element = self.driver.driver.find_element(By.ID, 'username')
            if search_element is None:
                print("... Could not find username field")
                self.log_step_error(
                    "password", message="could not find username field", integrity=login_page_integrity)
                return err
            search_element.send_keys(self.username)
            sleep(1)

            # Attempt to locate and fill in the password field
            print(f"... Trying to enter password '{self.password}'")
            self.log_step_start("password")
            search_element = self.driver.driver.find_element(By.ID, 'password')
            if search_element is None:
                print("... Could not find password field")
                self.log_step_error(
                    "password", message="could not find password field", integrity=login_page_integrity)
                return err
            search_element.send_keys(self.password)

            self.log_step_success("password", integrity=login_page_integrity)

            sleep(1)

            # Attempt to locate and click the login button
            self.log_step_start("login-button")
            print("... Trying to click login")
            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
            search_element = self.driver.driver.find_element(
                By.TAG_NAME, 'button')
            if search_element is None:
                print("... Could not find login button")
                self.log_step_error(
                    "login-button", message="could not find login button")
                return err
            ActionChains(self.driver.driver).move_to_element(
                search_element).click(search_element).perform()
            # Temporarily delay to allow the secure page to load
            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        except Exception:
            # If any element is missing, assume we may already be logged in
            print("... No login fields present, assuming we're already logged in")
            pass

        # Attempt to locate the secured content on the post-login page
        print("... Checking that secure page loaded")

        secure_page_integrity = self.check_integrity()

        search_element = self.driver.driver.find_element(
            By.XPATH, '/html/body/p')
        if search_element is None:
            print("Could not find body paragraph of secured page")
            self.log_step_error("secure-page-loaded",
                                integrity=secure_page_integrity)
            return err

        # Determine success of login based on expected text
        if 'xample paragraph for a secure director' in search_element.text:
            print(f"Login successful with: {search_element.text}")
            err = False
            # Log login result including integrity status
            self.log_step_success("secure-page-loaded",
                                  integrity=secure_page_integrity)
        else:
            print(f"Login failed with: {search_element.text}")
            self.log_step_error("secure-page-loaded",
                                integrity=secure_page_integrity)

        # Occasionally log out for realism
        if random.random() < 0.2:
            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
            print("... Decided to log out")
            try:
                search_element = self.driver.driver.find_element(
                    By.ID, 'logout')
            except Exception:
                pass
            else:
                if search_element is not None:
                    ActionChains(self.driver.driver).move_to_element(
                        search_element).click(search_element).perform()
                else:
                    print("... Could not find logout link")
            print("... Stopping browser to force logout")
            self.driver.stop_browser()
        else:
            print("... Decided not to log out")

        return err
