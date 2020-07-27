from os import name as osname

timeout_settings = "network.dns.resolver_shutdown_timeout_ms," \
                   "network.ftp.idleConnectionTimeout," \
                   "network.http.connection-retry-timeout," \
                   "network.http.keep-alive.timeout," \
                   "network.http.response.timeout," \
                   "network.http.spdy.timeout," \
                   "network.http.tls-handshake-timeout," \
                   "network.proxy.failover_timeout," \
                   "network.tcp.tcp_fastopen_http_stalls_timeout," \
                   "network.trr.request-timeout," \
                   "network.websocket.timeout.close," \
                   "network.http.connection-timeout," \
                   "network.websocket.timeout.open".split(",")

gecko_driver_url = "https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz"

os = dict(posix="linux", nt="windows")[osname]