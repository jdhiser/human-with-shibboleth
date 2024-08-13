

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
        if self.username is None:
            self.get_creds(extra)
        self.shib_sign_in()

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


    def shib_sign_in(self):
        # Navigate to moodle
        self.driver.driver.get('https://service.castle.os/moodle')
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

            ActionChains(self.driver.driver).move_to_element(
                    search_element).click(search_element).perform()

            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
        except:
            print("... No login fields present, assuming we're already logged in")

        print("... Checking that secure page loaded")

        search_element = self.driver.driver.find_element(By.XPATH,
                "//h1[text()='Moodle for Castle']")
        if search_element is None:
            print("... Could not find Moodle welcome text element")
            return

        if 'oodle for Castl' in search_element.text:
            print(f"... Login successful with: {search_element.text}")
        else:
            print(f"... Login failed with: {search_element.text}")

        err = self.moodle_workflow()

        if err or random.random() < 0.2:
            print("... Decided to log out")
            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
            print("... Stopping browser to force logout")
            self.driver.stop_browser() # restart browser for security!
        else:
            print("... Decided not to log out of moodle")

    def moodle_workflow(self):

        search_element = self.driver.driver.find_element(By.XPATH, "//a[text()='Log in']")
        if search_element is None:
            print("... Could not find log in to moodle button")
            return True

        ActionChains(self.driver.driver).move_to_element(
                search_element).click(search_element).perform()
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        if self.first_time:
            if self.moodle_login(self.adminname, self.adminpass):
                return True
            if self.add_user(self.username, self.password):
                return True
            self.first_time=False
            if self.moodle_logout():  # log out of admin account.
                return True


        return False

    def moodle_login(self,name,passwd):
        search_element = self.driver.driver.find_element(By.ID, 'username') # username
        if search_element is None:
            print("... Could not find username field")
            return True

        search_element.send_keys(name)
        sleep(1)
        print(f"... Trying to enter password '{passwd}'")

        search_element = self.driver.driver.find_element(By.ID, 'password') # password
        if search_element is None:
            print("... Could not find username field")
            return True

        search_element.send_keys(passwd)

        sleep(1)
        print("... Trying to click login")

        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
        search_element = self.driver.driver.find_element(By.ID, 'loginbtn') # login button
        if search_element is None:
            print("... Could not find login button")
            return True

        ActionChains(self.driver.driver).move_to_element(
                search_element).click(search_element).perform()
        return False


    def moodle_logout(self):

        # logout dropdown
        print("... Trying to click user menu")
        search_element = self.driver.driver.find_element(By.ID, 'user-menu-toggle')
        if search_element is None:
            print("... Could not find user menu button")
            return True

        ActionChains(self.driver.driver).move_to_element(
                search_element).click(search_element).perform()

        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        print("... Trying to click log out item in user menu")
        search_element = self.driver.driver.find_element(By.XPATH, "//a[contains(@href,'logout')]")

        if search_element is None:
            print("... Could not find log out button in user menu")
            return True
        # print(f"Search element href is {search_element.getAttribute('href')}")

        sleep(3)
        ActionChains(self.driver.driver).click(search_element).perform()
        return False


    def add_user(self,name,passwd):
        self.driver.driver.get('https://service.castle.os/moodle/admin/user.php')
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        print("... Checking if user already exists")
        search_element = self.driver.driver.find_elements(
                By.XPATH, f"//td[text()='{name}@castle.os']")
        if len(search_element) == 0:
            print("... Could not find user account, adding it now.")
            return self.add_user_account(name,passwd)
        return False

    def add_user_account(self,name,passwd):
        print(f"... Adding new user {name}.")
        self.driver.driver.get('https://service.castle.os/moodle/user/editadvanced.php?id=-1')

        if self.enter_text("id_username", name, "user name"):
            return True

        search_element = self.driver.driver.find_element(By.XPATH, "//em[text()='Click to enter text']")
        if search_element is None:
            print("... Could not find new password field")
            return True
        ActionChains(self.driver.driver).move_to_element(
                search_element).click(search_element).perform()
        if self.enter_text("id_newpassword", passwd, "password"):
            return True
        if self.enter_text("id_firstname", self.fake.first_name(), "first name"):
            return True
        if self.enter_text("id_lastname", self.fake.last_name(), "last name"):
            return True
        if self.enter_text("id_email", name+"@castle.os", "email"):
            return True
        if self.enter_text("id_description_editor_ifr", self.fake.text(), "description"):
            return True
        search_element = self.driver.driver.find_element(By.ID, "id_submitbutton")
        if search_element is None:
            print("... Could not find submit button")
            return True
        print("... Found submit button")
        ActionChains(self.driver.driver).move_to_element(
                search_element).click(search_element).perform()
        print("... Completed user setup.")
        sleep(30)
        return False

    def enter_text(self, id_to_search_for, text_to_enter, msg_text):
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
        search_element = self.driver.driver.find_element(By.ID, id_to_search_for)

        if search_element is None:
            print(f"... Could not find {msg_text}")
            return True

        print(f"... Found {msg_text}")
        ActionChains(self.driver.driver).move_to_element(search_element).perform()
        search_element.send_keys(text_to_enter)
        return False
