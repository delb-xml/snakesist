class SnakesistError(Exception):
    """Snakesist base exception class"""

    pass


class ConfigurationError(SnakesistError):
    """Raised if the database connection is improperly configured"""

    pass


class ReadError(SnakesistError):
    """Raised if a writing operation fails"""

    pass


class NotFound(ReadError):
    """Raised if a database resource is not found"""

    pass


class WriteError(SnakesistError):
    """Raised if a reading operation fails"""

    pass
