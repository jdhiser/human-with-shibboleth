from time import sleep
import os
import random

# from soupsieve import select

from ..utility.base_workflow import BaseWorkflow
from ..utility.webdriver_helper import WebDriverHelper
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import ElementNotInteractableException

WORKFLOW_NAME = 'ShibbolethBrowser'
WORKFLOW_DESCRIPTION = 'Browse a website secured by Shibboleth'

DEFAULT_INPUT_WAIT_TIME = 2
MIN_WATCH_TIME = 2 # Minimum amount of time to watch a video, in seconds
MAX_WATCH_TIME = 150 # Maximum amount of time to watch a video, in seconds
MIN_WAIT_TIME = 2 # Minimum amount of time to wait after searching, in seconds
MAX_WAIT_TIME = 5 # Maximum amount of time to wait after searching, in seconds
MAX_SUGGESTED_VIDEOS = 10

SEARCH_LIST = 'browse_youtube.txt'

def load():
    driver = WebDriverHelper()
    return ShibbolethBrowse(driver=driver)


class ShibbolethBrowse(BaseWorkflow):

    def __init__(self, driver, input_wait_time=DEFAULT_INPUT_WAIT_TIME):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION, driver=driver)

        self.input_wait_time = input_wait_time

    def action(self, extra=None):
        self.sign_in()

    """ PRIVATE """

    def sign_in(self):
        random_search = self._get_random_search()

        # Navigate to youtube
        self.driver.driver.get('https://service.castle.os/secure/index.html')
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))


