import httpx
from _delb.nodes import TagNode

from snakesist.utils import _parse_tag_node


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


class SnakesistQueryError(SnakesistError):
    """Informs about query errors."""

    __slots__ = ("messages", "path", "payload")

    def __init__(self, payload: str, response: httpx.Response):
        exception = _parse_tag_node(response.text)
        assert exception.local_name == "exception"

        self.messages: tuple[str, ...] = tuple(
            n.full_text for n in exception.css_select("message")
        )
        self.path = exception.css_select("path").first.full_text
        self.payload = payload

        super().__init__()

    def __str__(self) -> str:
        lines = [f"Exceptions raised when querying on collection `{self.path}`:", ""]
        lines.extend(f"- {x}" for x in self.messages)
        lines.extend(["", "Payload:", "", self.payload])
        return "\n".join(lines)


class SnakesistWriteError(SnakesistError):
    """Raised if a reading operation fails"""

    pass
