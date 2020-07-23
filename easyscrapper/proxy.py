import asyncio
from multiprocessing import Process, Queue

import numpy as np
from proxybroker import Broker

from easylogger import LoggingClass


class FindProxyError(Exception):
    def __init__(self):
        super(FindProxyError, self).__init__("Unable to find proxy. Are you connected to internet? "
                                             "Is proxybrocker installed?")


class RandomQueue(list):
    def __init__(self):
        super(RandomQueue, self).__init__()
        self.queue = Queue()

    def put(self, value):
        self.queue.put(value)

    def get(self, timeout=None):
        if timeout is not None and len(self) == 0 and self.queue.qsize() == 0:
            return self.queue.get(timeout=timeout)
        N = self.queue.qsize()
        for i in range(N):
            self.append(self.queue.get(timeout=0))
        i = np.random.randint(0, len(self))
        res = self.pop(i)
        return res

    def qsize(self):
        return len(self) + self.queue.qsize()


class PBrocker(Process, LoggingClass):
    def __init__(self):
        Process.__init__(self)
        LoggingClass.__init__(self)
        self.data = RandomQueue()
        self.proxies = proxies = asyncio.Queue()
        self.brocker = Broker(proxies)
        self.loop = asyncio.get_event_loop()

    def run(self) -> None:
        self.debug("Starting loop")
        tasks = asyncio.gather(
            self.brocker.find(types=['HTTP', 'HTTPS'], limit=np.inf),
            self.save(),
        )
        self.loop.run_until_complete(tasks)
        self.debug("Finished run")

    async def save(self):
        """Save proxies to a file."""
        while True:
            proxy = await self.proxies.get()
            if proxy is None:
                break
            proxy = (proxy.host, proxy.port)
            self.append(proxy)

    def append(self, value):
        # self.log.debug(f"Found new proxy: {value}. Queue has size {self.data.qsize()}")
        self.data.put(value)

    def stop(self):
        self.log.debug("Stopping brocker")
        self.brocker.stop()
        self.__stopped = True

    def start(self) -> None:
        super(PBrocker, self).start()

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        self.debug(f"Joining")
        self.join()
