from time import sleep
import random

# from soupsieve import select

from ..utility.base_workflow import BaseWorkflow
from ..utility.webdriver_helper import WebDriverHelper
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

WORKFLOW_NAME = 'ShibbolethBrowser'
WORKFLOW_DESCRIPTION = 'Browse a website secured by Shibboleth'

DEFAULT_INPUT_WAIT_TIME = 2
MIN_WAIT_TIME = 2 # Minimum amount of time to wait after searching, in seconds
MAX_WAIT_TIME = 5 # Maximum amount of time to wait after searching, in seconds

SEARCH_LIST = 'browse_youtube.txt'

def load():
    driver = WebDriverHelper()
    return ShibbolethBrowse(driver=driver)


class ShibbolethBrowse(BaseWorkflow):

    def __init__(self, driver, input_wait_time=DEFAULT_INPUT_WAIT_TIME):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION, driver=driver)
        self.username=None
        self.password=None




    def action(self, extra=None):
        if self.username is None:
            self.get_creds(extra)
        self.sign_in()

    """ PRIVATE """

    def get_creds(self, extra=None):
        self.username='jdh'
        self.password='jdhpass'
        
        passfile=None
        if len(extra)==2:
            if extra[0] == "passfile":
                with open(extra[1]) as f:
                    self.username = f.readline().strip()
                    self.password = f.readline().strip()


    def sign_in(self):
        # Navigate to youtube
        self.driver.driver.get('https://service.castle.os/secure/index.html')
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))


        try:
            print(f"... Trying to enter username '{self.username}'")

            search_element = self.driver.driver.find_element(By.ID, 'username') # username
            if search_element is None:
                print("... Could not find username field")
                return

            search_element.send_keys(self.username)
            sleep(1)
            print(f"... Trying to enter password '{self.password}'")

            search_element = self.driver.driver.find_element(By.ID, 'password') # password
            if search_element is None:
                print("... Could not find username field")
                return

            search_element.send_keys(self.password)

            sleep(1)
            print("... Trying to click login")

            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
            search_element = self.driver.driver.find_element(By.TAG_NAME, 'button') # login button
            if search_element is None:
                print("... Could not find login button")
                return

            ActionChains(self.driver.driver).move_to_element(search_element).click(search_element).perform()

            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
        except:
            print("... No login fields present, assuming we're already logged in")
            pass

        print("... Checking that secure page loaded")

        search_element = self.driver.driver.find_element(By.XPATH, '/html/body/p') # main body paragraph
        if search_element is None:
            print("... Could not find body paragraph of secured page")
            return

        if 'example paragraph for a secure directory.' in search_element.text:
            print("... Login successful!")
        else:
            print(f"... Login failed with: {search_element.text}")

        
        if random.random() < 0.2:
            print("... Decided to log out")
            search_element = self.driver.driver.find_element(By.ID, 'logout') # logout button
            if search_element is None:
                print("... Could not find logout link")
                return
            ActionChains(self.driver.driver).move_to_element(search_element).click(search_element).perform()
            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
            print("... Stopping browser to force logout")
            self.driver.stop_browser() # restart browser for security!
        else:
            print("... Decided not to log out")

        


