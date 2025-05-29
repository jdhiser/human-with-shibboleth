import os
import getpass

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.driver_cache import DriverCacheManager
from webdriver_manager.core.manager import DriverManager
from webdriver_manager.drivers.chrome import ChromeDriver

from .base_driver import BaseDriverHelper

DRIVER_NAME = 'ChromeWebDriver'

class WebDriverHelper(BaseDriverHelper):



    def __init__(self):
        super().__init__(name=DRIVER_NAME)
        username = getpass.getuser()
        user_tmp_dir = f"/tmp/chrome-profile-{username}"
        cache_dir = os.path.join(user_tmp_dir, "wdm-cache")
        os.makedirs(cache_dir, exist_ok=True)

        # Force environment cache isolation
        os.environ["WD_MANAGER_CACHE_PATH"] = cache_dir
        os.environ["XDG_CACHE_HOME"] = os.path.join(user_tmp_dir, ".cache")
        os.environ["XDG_CONFIG_HOME"] = os.path.join(user_tmp_dir, ".config")

        # Set up Chrome options
        self.options = webdriver.ChromeOptions()
        self.options.add_argument(f'--user-data-dir={user_tmp_dir}')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--ignore-certificate-errors')
        self.options.add_argument('--start-maximized')
        self.options.add_argument('--disable-infobars')

        # Manually create cache manager
        cache_manager = DriverCacheManager(cache_dir)
        self._driver_path = ChromeDriverManager(cache_manager=cache_manager).install()

        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = webdriver.Chrome(service=Service(self._driver_path), options=self.options)
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
