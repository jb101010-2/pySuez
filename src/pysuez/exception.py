class PySuezError(Exception):
    pass


class PySuezConnexionError(PySuezError):
    pass


class PySuezConnexionNeededException(PySuezConnexionError):
    pass


class PySuezDataError(PySuezError):
    pass
