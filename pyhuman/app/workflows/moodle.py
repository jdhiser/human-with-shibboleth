

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=relative-beyond-top-level
# pylint: disable=unused-argument
# pylint: disable=bare-except
# pylint: disable=too-many-return-statements

from time import sleep
import random

from faker import Faker
from faker.providers import person

# from soupsieve import select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from ..utility.base_workflow import BaseWorkflow
from ..utility.webdriver_helper import WebDriverHelper

WORKFLOW_NAME = 'Moodle'
WORKFLOW_DESCRIPTION = 'Interact with Moodle'

DEFAULT_INPUT_WAIT_TIME = 2
MIN_WAIT_TIME = 2 # Minimum amount of time to wait after searching, in seconds
MAX_WAIT_TIME = 5 # Maximum amount of time to wait after searching, in seconds

def load():
    driver = WebDriverHelper()
    return MoodleBrowse(driver=driver)

class MoodleBrowse(BaseWorkflow):

    def __init__(self, driver, input_wait_time=DEFAULT_INPUT_WAIT_TIME):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION, driver=driver)
        self.username='jdh'
        self.password='jdhpass'
        self.user_roles = ['admin']
        self.first_time = True
        self.adminname='admin'
        self.adminpass='adminPass!1'
        self.fake = Faker()
        self.fake.add_provider(person)


    def action(self, extra=None):
        self.get_creds(extra)
        err = self.shib_sign_in()
        err = err or self.moodle_workflow()

        if err or random.random() < 0.2:
            print("... Decided to log out")
            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
            print("... Stopping browser to force logout")
            self.driver.stop_browser() # restart browser for security!
        else:
            print("... Decided not to log out of moodle")

    # PRIVATE

    def get_creds(self, extra=None):
        self.user_roles = []

        i = 0
        while i < len(extra):
            if extra[i] == "passfile":
                with open(extra[i+1], encoding="utf-8") as file:
                    self.username = file.readline().strip()
                    self.password = file.readline().strip()
                i += 2
            elif extra[i] == "user_roles":
                self.user_roles=extra[i+1].split(',')
                i += 2
            else:
                i += 1


    def shib_sign_in(self) -> bool:
        # Navigate to moodle
        self.driver.driver.get('https://service.castle.os/moodle/auth/shibboleth/index.php')
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))


        try:
            print(f"... Trying to enter username '{self.username}'")

            search_element = self.driver.driver.find_element(By.ID, 'username') # username
            if search_element is None:
                print("... Could not find username field")
                return True

            search_element.send_keys(self.username)
            sleep(1)
            print(f"... Trying to enter password '{self.password}'")

            search_element = self.driver.driver.find_element(By.ID, 'password') # password
            if search_element is None:
                print("... Could not find username field")
                return True

            search_element.send_keys(self.password)

            sleep(1)
            print("... Trying to click login")

            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
            search_element = self.driver.driver.find_element(By.TAG_NAME, 'button') # login button
            if search_element is None:
                print("... Could not find login button")
                return True

            ActionChains(self.driver.driver).move_to_element(
                    search_element).click(search_element).perform()

            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
        except:
            print("... No login fields present, assuming we're already logged in")

        print("... Checking that Moodle Dashboard loaded")


        search_str = f"Hi, {self.username}"
        search_element = self.driver.driver.find_element(By.XPATH,
                f"//*[contains(text(),'{search_str}')]")
        if search_element is None:
            print("... Could not find Moodle Dashboard text element")
            return True

        if not search_str in search_element.text:
            print(f"... Login failed with: {search_str} not in {search_element.text}")
            return True
        print(f"... Login successful with: {search_element.text}")
        return False


    def enrol_in_course(self) -> bool:
        self.driver.driver.get('https://service.castle.os/moodle/?redirect=0')
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        err = self.find_text_and_click('Special Topics: AI-Powered Cybersecurity')
        err = err or self.find_text_and_click('Enrol me in this course')
        err = err or self.find_id_and_click('id_submitbutton')

        return err

    def moodle_workflow(self) -> bool:
        self.driver.driver.get('https://service.castle.os/moodle/my/courses.php')
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        search_str = "not enrolled in any course"
        search_elements = self.driver.driver.find_elements(By.XPATH,
                f"//*[contains(text(),'{search_str}')]")

        err = False
        print(f"{search_elements}")
        if len(search_elements) != 0:
            print(" ... Enrolling in a course")
            err = self.enrol_in_course()
        else:
            print(" ... already enrolled in a course!")

        err = err or self.browse_course()
        return err


    def browse_course(self) -> bool:
        return False


    def find_text_and_click(self, to_find: str) -> bool:

        search_element = self.driver.driver.find_element(By.XPATH,
                f"//*[contains(text(),'{to_find}')]")

        if search_element is None or not to_find in search_element.text:
            print(f" ... could not find text '{to_find}'")
            return True

        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
        print(f"... Trying to click {to_find}")
        ActionChains(self.driver.driver).move_to_element(
                search_element).click(search_element).perform()

        return False



    def find_id_and_click(self, to_find: str) -> bool:
        search_element = self.driver.driver.find_element(By.ID, to_find)

        if search_element is None:
            print(f" ... could not find button id='{to_find}'")
            return True

        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
        print(f"... Trying to click button id={to_find}")
        ActionChains(self.driver.driver).move_to_element(
                search_element).click(search_element).perform()

        return False
