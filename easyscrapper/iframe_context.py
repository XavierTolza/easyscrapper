class IframeContext(object):
    def __init__(self, driver, iframe):
        self.iframe = iframe
        self.driver = driver

    def __enter__(self):
        self.driver.switch_to.frame(self.iframe)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.switch_to.parent_frame()
