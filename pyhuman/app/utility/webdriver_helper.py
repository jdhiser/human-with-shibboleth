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

        home_dir = os.path.expanduser(f"~{username}")
        use_tmp = not os.path.isdir(home_dir)

        # Always create base Chrome options
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--ignore-certificate-errors')
        self.options.add_argument('--start-maximized')
        self.options.add_argument('--disable-infobars')

        cache_manager = None  # default

        if use_tmp:
            base_dir = f"/tmp/chrome-profile-{username}"
            cache_dir = os.path.join(base_dir, "wdm-cache")
            xdg_cache_dir = os.path.join(base_dir, ".cache")
            xdg_config_dir = os.path.join(base_dir, ".config")

            # Create necessary directories
            os.makedirs(cache_dir, exist_ok=True)
            os.makedirs(xdg_cache_dir, exist_ok=True)
            os.makedirs(xdg_config_dir, exist_ok=True)

            # Set environment variables to isolate from $HOME
            os.environ["WD_MANAGER_CACHE_PATH"] = cache_dir
            os.environ["XDG_CACHE_HOME"] = xdg_cache_dir
            os.environ["XDG_CONFIG_HOME"] = xdg_config_dir

            # Add user-data-dir argument if use_tmp
            self.options.add_argument(f'--user-data-dir={base_dir}')

            # Use custom cache manager
            cache_manager = DriverCacheManager(cache_dir)

        self._driver_path = ChromeDriverManager(
            cache_manager=cache_manager).install()
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = webdriver.Chrome(service=Service(
                self._driver_path), options=self.options)
        return self._driver

    def stop_browser(self):
        # quit() talks to chromedriver over HTTP, so when the driver is the
        # thing that has hung, this is exactly the call that cannot complete:
        # it raises ReadTimeoutError after urllib3 burns its three 120 s
        # retries. The assignment below used to sit after an unguarded quit(),
        # so it never ran, and because this class is a Singleton the dead
        # driver stayed installed -- every later workflow in the run picked it
        # up again and timed out against the same port.
        #
        # Round 39 CI #958 is the example: browse_web hung, "Trying browser
        # restart" was printed, and the three retries that followed all went
        # to the same localhost:52703 that had already stopped answering.
        #
        # Dropping the reference is the part that matters -- get_driver()
        # lazily builds a fresh driver when it is None -- so it happens in
        # finally, whether or not the polite shutdown works.
        if self._driver is None:
            return
        try:
            self._driver.quit()
        except Exception as e:  # noqa: BLE001
            print(f"stop_browser: quit() failed ({type(e).__name__}: {e}); "
                  "dropping the driver reference anyway")
        finally:
            self._driver = None

    def restart_browser(self):
        # Same hazard: a hung driver must not stop us building a new one.
        self.stop_browser()
        return self.get_driver()

    def cleanup(self):
        self.stop_browser()

    """ PRIVATE """

    def check_valid_driver_connection(self):
        try:
            driver = webdriver.Chrome(self._driver_path)
            driver.quit()
            return True
        except Exception as e:
            print('Could not load ChromeDriver: {0}'.format(e))
            return False
