class PySuezError(Exception):
    pass


class PySuezConnexionError(PySuezError):
    pass


class PySuezDataError(PySuezError):
    pass
