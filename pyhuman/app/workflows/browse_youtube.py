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
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.keys import Keys

WORKFLOW_NAME = 'YoutubeBrowser'
WORKFLOW_DESCRIPTION = 'Browse Youtube'

DEFAULT_INPUT_WAIT_TIME = 2
MIN_WATCH_TIME = 2  # Minimum amount of time to watch a video, in seconds
MAX_WATCH_TIME = 150  # Maximum amount of time to watch a video, in seconds
MIN_WAIT_TIME = 2  # Minimum amount of time to wait after searching, in seconds
MAX_WAIT_TIME = 5  # Maximum amount of time to wait after searching, in seconds
MAX_SUGGESTED_VIDEOS = 10

SEARCH_LIST = 'browse_youtube.txt'

# YouTube has moved the search box more than once, and an EU-style consent
# interstitial can sit in front of the whole page. Try the known shapes in
# order rather than pinning one: 'input#search' alone silently stopped
# matching and the workflow failed with a bare NoSuchElementException that
# said nothing about why.
SEARCH_BOX_SELECTORS = (
    'input#search',                       # long-standing desktop layout
    'input[name="search_query"]',         # current markup
    'ytd-searchbox input',                # wrapped form
    'div#search-input input',
    'input[aria-label="Search"]',
)

# Consent / cookie interstitials. Clicking any of these gets us to the page;
# none of them existing is also fine.
CONSENT_SELECTORS = (
    'button[aria-label*="Accept"]',
    'button[aria-label*="Reject"]',
    'form[action*="consent"] button',
    'tp-yt-paper-button#button',
)


def load():
    driver = WebDriverHelper()
    return YoutubeSearch(driver=driver)


class YoutubeSearch(BaseWorkflow):

    def __init__(self, driver, input_wait_time=DEFAULT_INPUT_WAIT_TIME):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION, driver=driver)

        self.input_wait_time = input_wait_time
        self.search_list = self._load_search_list()

    def action(self, extra=None):
        self._search_web()

    """ PRIVATE """

    def _search_web(self):
        random_search = self._get_random_search()

        # Navigate to youtube
        self.driver.driver.get('https://www.youtube.com')
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        self._dismiss_consent()

        # Perform a youtube search
        search_element = self._find_search_box()
        search_element.send_keys(random_search)
        # RETURN, not .submit(): the search box is not always inside a <form>,
        # and Selenium 4 raises on submit() when it is not.
        search_element.send_keys(Keys.RETURN)
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        # Click on a random video from the search results
        WebDriverWait(self.driver.driver, 10).until(
            EC.presence_of_all_elements_located((By.ID, "video-title")))
        search_results = self.driver.driver.find_elements(By.ID, "video-title")
        attempts = 0
        while attempts < 10:
            try:
                search_results[random.randrange(0, len(search_results))].click()
                attempts = 10
            except Exception:
                attempts += 1
                print("... Failed to click, retrying.")

        sleep(random.randrange(MIN_WATCH_TIME, MAX_WATCH_TIME))

        # Click on a random video from the suggested videos
        for _ in range(0, random.randrange(0, MAX_SUGGESTED_VIDEOS)):
            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
            suggested_videos = self.driver.driver.find_elements(
                By.ID, "video-title")
            try:
                suggested_videos[random.randrange(0, len(suggested_videos))].click()
            except ElementNotInteractableException:
                pass
            except ElementClickInterceptedException:
                pass

    def _dismiss_consent(self):
        """Click through a consent/cookie interstitial if one is present.

        Best-effort: absence is the normal case and must not be an error.
        """
        for sel in CONSENT_SELECTORS:
            try:
                for el in self.driver.driver.find_elements(By.CSS_SELECTOR, sel):
                    if el.is_displayed() and el.is_enabled():
                        el.click()
                        sleep(DEFAULT_INPUT_WAIT_TIME)
                        return True
            except Exception:
                continue
        return False

    def _find_search_box(self):
        """Return YouTube's search input, trying each known selector.

        Raises with the list actually tried, so a future layout change reports
        what it looked for instead of a bare NoSuchElementException.
        """
        last = None
        for sel in SEARCH_BOX_SELECTORS:
            try:
                el = WebDriverWait(self.driver.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                if el:
                    return el
            except (TimeoutException, NoSuchElementException) as e:
                last = e
                continue
        raise NoSuchElementException(
            "YouTube search box not found. Tried: "
            + ", ".join(SEARCH_BOX_SELECTORS)
            + f". Page title was {self.driver.driver.title!r}, url "
            + f"{self.driver.driver.current_url!r}. YouTube's layout has most "
            "likely changed again -- add the new selector to "
            f"SEARCH_BOX_SELECTORS. Last error: {last}")

    def _get_random_search(self):
        search_term = random.choice(self._load_search_list()).rstrip('\n')
        return search_term

    @staticmethod
    def _load_search_list():
        with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..',
                                               'data', SEARCH_LIST))) as f:
            wordlist = f.readlines()
        return wordlist
