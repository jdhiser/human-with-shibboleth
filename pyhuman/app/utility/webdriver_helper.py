import os
import getpass
import re
import shutil
import subprocess
import urllib.request
import zipfile

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.driver_cache import DriverCacheManager
from webdriver_manager.core.manager import DriverManager
from webdriver_manager.drivers.chrome import ChromeDriver

from .base_driver import BaseDriverHelper

DRIVER_NAME = 'ChromeWebDriver'


# Offline chromedriver.
#
# ChromeDriverManager().install() asks the internet which chromedriver goes
# with the installed Chrome, every time a browser workflow loads. Air-gapped
# that is fatal and not obviously a network problem:
#
#   Error could not load workflow browse_iis.py: Could not reach host.
#   Are you offline?
#
# It stayed hidden because the offline workflow set used to run AFTER
# configure-vms.py had restored egress, so the browser workflows always had
# the internet they were supposed to be proving they did not need.
#
# Read the marker file rather than the environment: pyhuman is launched from
# a non-interactive context that does not source /etc/profile.d.
def _offline_base():
    base = (os.environ.get('CASTLE_OFFLINE_BASE') or '').strip()
    if not base:
        try:
            with open('/etc/profile.d/castle-offline.sh') as fh:
                for line in fh:
                    if line.startswith('export CASTLE_OFFLINE_BASE='):
                        base = line.split('=', 1)[1].strip().strip('"').strip("'")
        except OSError:
            base = ''
    return base.rstrip('/')


def _chrome_major():
    """Major version of the installed Chrome, or None."""
    for exe in ('google-chrome', 'google-chrome-stable', 'chromium'):
        try:
            out = subprocess.run([exe, '--version'], capture_output=True,
                                 text=True, timeout=30).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        m = re.search(r'(\d+)\.', out or '')
        if m:
            return m.group(1)
    return None


def offline_chromedriver():
    """
    chromedriver from the package store, matched to the installed Chrome.

    Returns a path, or None when not offline. Raises when offline and the
    store cannot supply a matching driver -- a loud failure here beats
    falling through to ChromeDriverManager, which would fail with a network
    error that says nothing about the real cause.

    The major version has to match: these hosts carry Chrome from the base
    image (154) while the store's own .deb is a different line (158), and
    the snap chromium-chromedriver on PATH is a major BEHIND the Chrome it
    sits next to, so "there is a chromedriver installed" is not enough.
    """
    base = _offline_base()
    if not base:
        return None

    major = _chrome_major()
    if not major:
        raise RuntimeError("offline: no Chrome found, cannot pick a chromedriver")

    cached = os.path.join('/tmp', f'castle-chromedriver-{major}', 'chromedriver')
    if os.path.isfile(cached) and os.access(cached, os.X_OK):
        return cached

    url = f'{base}/files/chromedriver/chromedriver-{major}-linux64.zip'
    dest_dir = os.path.dirname(cached)
    os.makedirs(dest_dir, exist_ok=True)
    tmp_zip = os.path.join(dest_dir, 'chromedriver.zip')
    try:
        urllib.request.urlretrieve(url, tmp_zip)
    except Exception as exc:
        raise RuntimeError(
            f"offline: no chromedriver for Chrome {major} in the store "
            f"({url}): {exc}. Add it to manifest.yaml under files/.") from exc

    with zipfile.ZipFile(tmp_zip) as z:
        member = next(n for n in z.namelist() if n.endswith('/chromedriver'))
        with z.open(member) as src, open(cached, 'wb') as dst:
            shutil.copyfileobj(src, dst)
    os.chmod(cached, 0o755)
    os.remove(tmp_zip)
    return cached


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

        self._driver_path = (offline_chromedriver()
                             or ChromeDriverManager(
                                 cache_manager=cache_manager).install())
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
