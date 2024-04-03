from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from .base_driver import BaseDriverHelper

DRIVER_NAME = 'ChromeWebDriver'

class WebDriverHelper(BaseDriverHelper):

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")

    def __init__(self):
        super().__init__(name=DRIVER_NAME)
        self._driver_path = ChromeDriverManager().install()
        self._driver = None

    @property
    def driver(self):
        if self._driver == None:
            self._driver = webdriver.Chrome(self._driver_path, options=self.options)
        return self._driver

    def stop_browser(self):
        if self._driver == None:
            return
        self._driver.quit()
        self._driver = None

    def restart_browser(self):
        self._driver.quit()
        self._driver = webdriver.Chrome(self._driver_path, options=self.options)

    def cleanup(self):
        self._driver.quit()

    """ PRIVATE """

    def check_valid_driver_connection(self):
        try:
            driver = webdriver.Chrome(self._driver_path)
            driver.quit()
            return True
        except Exception as e:
            print('Could not load ChromeDriver: {0}'.format(e))
            return False
