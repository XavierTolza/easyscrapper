from selenium import webdriver
from selenium.webdriver import FirefoxProfile
from selenium.webdriver.firefox.options import Options

from easyscrapper.common import timeout_settings
from easyscrapper.generic_driver import GenericDriver


class Firefox(webdriver.Firefox, GenericDriver):

    def __init__(self, headless=True, download_pdf=False, timeout=10, download_dir=None, *args, **kwargs):
        self.__timeout = timeout
        self.download_dir = download_dir
        options = Options()
        options.headless = headless

        fp = None
        if headless:
            fp = self.empty_profile()
            fp.set_preference("http.response.timeout", timeout)
            fp.set_preference("dom.max_script_run_time", timeout)

        if download_pdf:
            if fp is None:
                fp = self.empty_profile()

            fp.set_preference("browser.download.folderList", 2)
            fp.set_preference("browser.helperApps.alwaysAsk.force", False)
            fp.set_preference("browser.download.manager.showWhenStarting", False)
            fp.set_preference("browser.download.dir", download_dir)
            fp.set_preference("plugin.disable_full_page_plugin_for_types", "application/pdf")
            fp.set_preference("pdfjs.disabled", True)
            fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")

        preferences = {i: timeout for i in timeout_settings}

        webdriver.Firefox.__init__(self, options=options, firefox_profile=fp)
        GenericDriver.__init__(self, *args, headless=headless, preferences=preferences, **kwargs)

    @property
    def timeout(self):
        return self.__timeout

    def empty_profile(self):
        return FirefoxProfile()

    def check_driver_is_installed(self):
        self.debug("Testing if gecko driver is installed")
        if not self.gecko_driver_installed():
            self.install_gecko_driver()
