import os
import re
import tarfile
from os import system, remove
from os.path import join, isfile, abspath
from tempfile import gettempdir
from time import time, sleep

import numpy as np
from easylogger import LoggingClass
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.firefox.options import Options
from user_agent import generate_user_agent

from .common import gecko_driver_url
from .common import os as osname
from .errors import ConnexionError
from .iframe_context import IframeContext
from .proxy import PBrocker
from .tools import wget


class AbstractDriver(object):
    abstract_error = NotImplementedError("This method is abstract")

    def execute_script(self, script):
        raise self.abstract_error

    @property
    def current_window_handle(self):
        raise self.abstract_error

    def empty_profile(self):
        raise self.abstract_error

    def check_driver_is_installed(self):
        raise self.abstract_error

    @property
    def switch_to(self):
        raise self.abstract_error

    @property
    def window_handles(self):
        raise self.abstract_error

    def close(self):
        raise self.abstract_error

    def get(self, *args, **kwargs):
        raise self.abstract_error

    def refresh(self, *args, **kwargs):
        raise self.abstract_error

    def execute(self, *args, **kwargs):
        raise self.abstract_error

    @property
    def timeout(self):
        raise self.abstract_error

    def find_element_by_css_selector(self, *args, **kwargs):
        raise self.abstract_error


class GenericDriver(AbstractDriver, LoggingClass):
    pref_types = {str: "String", int: "Int", bool: "Bool"}
    ip_finder = re.compile(".+[^\d](\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,6}).+")

    def __init__(self, headless, enable_cache=False, use_proxy_broker=False, preferences: dict = {}, **kwargs):
        self.use_proxy_broker = use_proxy_broker
        preferences.update({i: enable_cache for i in "browser.cache.disk.enable,browser.cache.memory."
                                                     "enable,browser.cache.offline.enable," \
                                                     "network.http.use-cache".split(",")})

        if not headless:
            self.maximize_window()

        if use_proxy_broker:
            self.broker = PBrocker()
        LoggingClass.__init__(self, **kwargs)

        self.debug("Setting preferences")
        self.set_preference(**preferences)

    @staticmethod
    def gecko_driver_installed():
        try:
            options = Options()
            options.headless = True
            d = webdriver.Firefox(options=options)
            d.close()
            d.quit()
            return True
        except WebDriverException as e:
            return False

    def new_tab(self, url=None):
        self.execute_script(f'window.open("","_blank");')
        self.tab = -1
        if url is not None:
            self.get(url)
        pass

    @property
    def tab(self):
        comp = np.array([self.current_window_handle]).ravel()[:, None] == np.ravel([self.window_handles])[None, :]
        res = np.argmax(np.ravel(comp))
        return res

    @tab.setter
    def tab(self, value):
        self.switch_to.window(self.window_handles[int(value)])

    def close_tab(self):
        self.execute_script(f'window.close();')
        self.switch_to.window(self.window_handles[-1])

    @property
    def n_tabs(self):
        return len(self.window_handles)

    def __enter__(self):
        if self.use_proxy_broker:
            self.broker.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.log.debug("Stopping scrapper")
        if self.use_proxy_broker:
            system(f"kill -9 {self.broker.pid}")
        while len(self.window_handles) > 1:
            self.tab = -1
            self.close_tab()
        self.close()

    def close(self):
        while self.n_tabs > 1:
            self.tab = -1
            self.close_tab()
        super(GenericDriver, self).close()

    def set_preference(self, **elements):
        self.debug(f"Setting preferences: {elements}")
        self.new_tab("about:config")

        try:
            script = """
            var prefs = Components.classes["@mozilla.org/preferences-service;1"]
                .getService(Components.interfaces.nsIPrefBranch);
            prefs.set%sPref(arguments[0], arguments[1]);
            """
            for key, value in elements.items():
                value_type = type(value)
                self.execute_script(script % self.pref_types[value_type], key, value)
        except KeyError:
            raise ValueError(f"Wrong type for pref {key} value: {str(value_type)}. Supported types are "
                             f"{list(self.pref_types.keys())}")
        finally:
            self.close_tab()
        return

    def disable_image_load(self):
        self.set_preference(**{"permissions.default.image": 0})
        # "dom.ipc.plugins.enabled.libflashplayer.so": False})

    def set_proxy(self, **kwargs):

        script = ["Services.prefs.setIntPref('network.proxy.type', 1);"]
        values = []
        for i, (k, v) in enumerate(kwargs.items()):
            script.append(f'Services.prefs.setCharPref("network.proxy.{k}", arguments[{i * 2}]);')
            values.append(v[0])
            script.append(f'Services.prefs.setIntPref("network.proxy.{k}_port", arguments[{i * 2 + 1}]);')
            values.append(v[1])
        script = "\n".join(script)

        self.new_tab("about:config")
        self.execute("SET_CONTEXT", {"context": "chrome"})
        try:
            self.execute_script(script, *values)

        finally:
            self.execute("SET_CONTEXT", {"context": "content"})
            self.close_tab()
        pass

    def enable_js(self):
        self.set_preference(**{"javascript.enabled": True})

    def disable_js(self):
        self.set_preference(**{"javascript.enabled": False})

    def get(self, url):
        self.info("Going to %s" % url)
        try:
            super(GenericDriver, self).get(url)
        except WebDriverException as e:
            raise ConnexionError(e)

    def refresh(self):
        try:
            super(GenericDriver, self).refresh()
        except WebDriverException as e:
            raise ConnexionError(e)

    def set_user_agent(self, value):
        self.set_preference(**{"general.useragent.override": value})

    def generate_user_agent(self, **kwargs):
        return generate_user_agent(**kwargs)

    def generate_proxy(self):
        queue = self.broker.data
        res = queue.get(timeout=self.timeout)
        return res

    def click_coordinates(self, element, x, y):
        ac = ActionChains(self)
        ac.move_to_element(element).move_by_offset(x, y).click().perform()

    def change_identity(self, proxy=True, user_agent=True):
        if proxy:
            proxy = self.generate_proxy()
            self.set_proxy(http=proxy, ssl=proxy)
        if user_agent:
            self.set_user_agent(self.generate_user_agent())

    def get_into_iframe(self, iframe):
        return IframeContext(self, iframe)

    def install_gecko_driver(self):
        self.debug("Asked to install gecko driver")
        geckodriverfilename = "geckodriver"
        folder = gettempdir()
        destfile = join(folder, "gecko.tar")

        if osname == "linux":
            paths = os.environ["PATH"].split(":")
        elif osname == "windows":
            paths = os.environ["PATH"].split(";")
        else:
            raise SystemError("Unsupported OS : %s" % os)

        for path in paths:
            dest_driver_file = join(path, geckodriverfilename)
            try:
                with open(dest_driver_file, "wb") as fp:
                    self.info(f"Installing gecko driver to {abspath(dest_driver_file)}")
                    wget(gecko_driver_url, destfile)
                    with tarfile.open(destfile) as tar:
                        data = tar.extractfile(tar.getmember(geckodriverfilename)).read()
                    fp.write(data)
                os.chmod(dest_driver_file, 0o0555)
                return
            except PermissionError as e:
                pass
            finally:
                if isfile(destfile):
                    remove(destfile)
        raise ValueError("Not writable folder found to put gecko driver")

    def css_element_exists(self, css: str):
        try:
            self.find_element_by_css_selector(css)
            return True
        except NoSuchElementException:
            return False

    def wait_for_css_element(self, css: str, timeout=10):
        self.debug("Waiting for CSS component %s with timeout %i" % (css, timeout))
        t0 = time()
        while (time() - t0) < timeout:
            if self.css_element_exists(css):
                return
            else:
                sleep(0.1)
        raise TimeoutError("Could not find css element %s" % css)
