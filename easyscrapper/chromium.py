import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from easyscrapper.generic_driver import GenericDriver


class Chromium(webdriver.Chrome, GenericDriver):
    def __init__(self, headless=True, download_dir=os.getcwd(), *args, **kwargs):
        self.download_dir = download_dir
        options = Options()
        options.headless = headless
        webdriver.Chrome.__init__(self, chrome_options=options)
        GenericDriver.__init__(self, headless=headless, *args, **kwargs)

    def set_preference(self, **elements):
        self.error("Setting preferences is not yet supported on chrome")


if __name__ == '__main__':
    driver = Chromium(headless=False)
    with driver:
        driver.get("https://google.com")
        pass
