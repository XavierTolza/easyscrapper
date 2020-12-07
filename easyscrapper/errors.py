import re

connexion_error_regex = re.compile(".+about:neterror\?e=([^&]+)&.+")


class ConnexionError(Exception):
    def __init__(self, e):
        err = str(e)
        _err = connexion_error_regex.match(err)
        if _err is not None:
            err = _err.groups()[0]
        super(ConnexionError, self).__init__(err)
