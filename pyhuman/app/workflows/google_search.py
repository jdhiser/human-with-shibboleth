import traceback
from time import sleep, time
import os
import random

from ..utility.metric_workflow import MetricWorkflow
from ..utility.webdriver_helper import WebDriverHelper
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

WORKFLOW_NAME = 'GoogleSearcher'
WORKFLOW_DESCRIPTION = 'Search for something on Google'
DEFAULT_WAIT_TIME = 2
MAX_PAGES = 5
MAX_NAVIGATION_CLICKS = 5

# Total wall-clock this workflow may spend, in seconds. Same reason as
# browse_youtube: emulate-logins forces login_length = 60 under --fast-debug
# and the success event only fires when action() returns, so up to 5 result
# pages plus 5 navigation clicks -- each a page load plus a 2 s sleep -- can
# outlive the window and never be recorded. A measured run took 56 s, which is
# inside 60 only by luck.
WORKFLOW_BUDGET_S = int(os.environ.get('PYHUMAN_GOOGLE_BUDGET_S', '35'))
SEARCH_LIST = 'google_searches.txt'


def load():
    driver = WebDriverHelper()
    return GoogleSearch(driver=driver)


class GoogleSearch(MetricWorkflow):

    def __init__(self, driver, input_wait_time=DEFAULT_WAIT_TIME):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION, driver=driver)

        self.input_wait_time = input_wait_time
        self.search_list = self._load_search_list()

    def action(self, extra=None):
        """
        Main entry point for the workflow.

        Returns:
            bool: True on error, False on success.
        """
        return self._search_web()

    """ PRIVATE """

    def _search_web(self):
        """Run one search. Returns True on error, False on success.

        The result has to be returned rather than swallowed: human.py's
        handle_workflow() logs a metric success unless action() reports an
        error, so a workflow that catches everything and returns None is
        recorded as having succeeded no matter what happened. This one did
        exactly that -- it logged 9-12 body-level successes on a host with no
        browser installed at all, which made its summary column 1/1
        unconditionally and meant CI could never fail on it.
        """
        self._deadline = time() + WORKFLOW_BUDGET_S
        random_search = self._get_random_search()
        try:
            # Navigate to google.com
            self.driver.driver.get('https://www.google.com')
            assert 'Google' in self.driver.driver.title
            sleep(DEFAULT_WAIT_TIME)

            # Randomly choose whether to google a search term or click lucky button
            chosen_action = random.choice(["search-term", "lucky"])

            if chosen_action == "search-term":
                self._google_search(random_search)
                sleep(DEFAULT_WAIT_TIME)
                self._browse_search_results()
                sleep(DEFAULT_WAIT_TIME)
                self._click_on_search_result()
            elif chosen_action == "lucky":
                self._hover_click_feeling_lucky(random_search)

            sleep(DEFAULT_WAIT_TIME)
            # Randomly navigate on the current website
            self._navigate_webpage()

        except Exception as e:
            print('Error performing google search %s: %s' %
                  (random_search.rstrip(), e))
            # Say WHERE it failed, not just that it did. Diagnosing the search
            # path previously meant guessing between "the results selector no
            # longer matches" and "Google served its /sorry bot-check page",
            # because neither the URL nor the title was ever recorded -- the
            # exception alone cannot tell them apart.
            try:
                drv = self.driver.driver
                url = drv.current_url
                print('At url  : %s' % url[:200])
                print('At title: %s' % (drv.title or '')[:120])
                blocked = '/sorry' in url or 'unusual traffic' in \
                    drv.find_element(By.TAG_NAME, 'body').text.lower()
                print('Looks like a bot-check page: %s' % blocked)
            except Exception as diag:
                print('(could not capture page context: %s)' % str(diag)[:100])
            print('At:')
            print(e)
            print(traceback.format_exc())
            return True

        return False

    def _click_on_search_result(self):
        """Click a result, located by structure rather than by CSS class.

        The old selector was CLASS_NAME "yuRUbf" -- one of Google's obfuscated
        build-generated classes, which changes without notice and had stopped
        matching. A result link is more durably described as "an anchor inside
        the results container that contains an h3 heading".
        """
        print(".... Clicking on search  result")
        results = WebDriverWait(self.driver.driver, 30).until(
            EC.visibility_of_any_elements_located(
                (By.XPATH, "//div[@id='search']//a[.//h3] | //div[@id='rso']//a[.//h3]")))
        search_result = results[0]
        ActionChains(self.driver.driver).move_to_element(
            search_result).click(search_result).perform()

    def _browse_search_results(self):
        # Click through search result pages
        print(".... Browsing search results")
        for _ in range(0, random.randint(0, MAX_PAGES)):
            if time() >= getattr(self, '_deadline', float('inf')):
                break

            # google doesn't have a next button anymore.  just infinit scroll
            # next_button = WebDriverWait(self.driver.driver, 30).until(EC.visibility_of_any_elements_located((By.LINK_TEXT, "Next")))[0]
            # ActionChains(self.driver.driver).move_to_element(next_button).click(next_button).perform()

            self.driver.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight)")
            sleep(DEFAULT_WAIT_TIME)

    def _google_search(self, random_search):
        """Type the query AND submit it.

        This used to type into the box and then scroll, never submitting, so
        the results page was never requested and _click_on_search_result sat
        waiting 30 s for results that could not appear. The workflow swallowed
        the resulting TimeoutException and reported success, which is why a
        search that never ran looked fine for so long.

        send_keys(RETURN) rather than submit(): Selenium 4 raises on submit()
        when the element is not inside a form, which is the case on Google's
        current page (same reason browse_youtube uses RETURN).
        """
        print(".... Googling:", random_search.rstrip())
        elem = self.driver.driver.find_element(By.NAME, 'q')
        elem.clear()
        sleep(self.input_wait_time)
        elem.send_keys(random_search)

        # Submit to whatever currently has focus, which is the box just typed
        # into. Two cheaper-looking approaches both fail on Google's current
        # page: sending RETURN to the element captured above raises
        # StaleElementReferenceException, because the autocomplete dropdown
        # re-renders the box while you type; and re-finding By.NAME 'q' raises
        # ElementNotInteractableException, because the page carries more than
        # one element named q and the first match is not the visible textarea.
        ActionChains(self.driver.driver).send_keys(Keys.RETURN).perform()

        WebDriverWait(self.driver.driver, 20).until(
            EC.presence_of_element_located((By.ID, "search")))
        self.driver.driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight)")

    def _hover_click_feeling_lucky(self, random_search=None):
        """Click "I'm Feeling Lucky", or fall back to an ordinary search.

        The button is not always present or visible on Google's current
        homepage, and when it is missing this waited the full 30 s and raised.
        Half of all runs pick this branch, so that alone made the workflow fail
        about half the time once it stopped swallowing errors. Not finding an
        optional button is not a failure of the workflow.
        """
        print(".... Hovering & clicking 'I'm Feeling lucky' button")
        try:
            element = WebDriverWait(self.driver.driver, 5).until(
                EC.visibility_of_any_elements_located(
                    (By.CSS_SELECTOR, '[name="btnI"]')))[0]
        except Exception:
            print(".... 'I'm Feeling lucky' not available; doing a normal search")
            self._google_search(random_search or self._get_random_search())
            sleep(DEFAULT_WAIT_TIME)
            self._click_on_search_result()
            return
        ActionChains(self.driver.driver).move_to_element(
            element).click(element).perform()

    def _navigate_webpage(self):
        # Navigate webpage
        navigation_clicks = random.randrange(0, MAX_NAVIGATION_CLICKS)
        print(".... Navigating and highlighting web page",
              navigation_clicks, "times")
        for _ in range(0, navigation_clicks):
            if time() >= getattr(self, '_deadline', float('inf')):
                break
            clickables = self.driver.driver.find_elements(By.TAG_NAME, ("a"))
            if len(clickables) == 0:
                return
            clickable = random.choice(clickables)
            try:
                self._highlight(clickable)
                self.driver.driver.execute_script(
                    "arguments[0].target='_self';", clickable)
                clickable.click()
                print("........ successful navigation")
            except Exception:
                print("........ X unsuccessful navigation")
                pass

    def _get_random_search(self):
        return random.choice(self.search_list)

    def _highlight(self, element):
        driver = element._parent

        def apply_style(s):
            driver.execute_script("arguments[0].setAttribute('style', arguments[1]);",
                                  element, s)
        original_style = element.get_attribute('style')
        apply_style("border: 10px solid red;")
        sleep(DEFAULT_WAIT_TIME)
        apply_style(original_style)

    @staticmethod
    def _load_search_list():
        with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..',
                                               'data', SEARCH_LIST))) as f:
            wordlist = f.readlines()
        return wordlist
