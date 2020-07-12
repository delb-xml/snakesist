class SnakesistError(Exception):
    """Snakesist base exception class"""

    pass


class SnakesistConfigError(SnakesistError):
    """Raised if the database connection is improperly configured"""

    pass


class SnakesistReadError(SnakesistError):
    """Raised if a writing operation fails"""

    pass


class SnakesistNotFound(SnakesistReadError):
    """Raised if a database resource is not found"""

    pass


class SnakesistWriteError(SnakesistError):
    """Raised if a reading operation fails"""

    pass
