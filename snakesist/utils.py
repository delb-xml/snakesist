import warnings
from typing import Optional

from _delb.nodes import TagNode
from _delb.parser import ParserOptions


# DROPWITH delb 0.6
def _parse_tag_node(
    source: str, parser_options: Optional[ParserOptions] = None
) -> TagNode:
    """Temporary facility to avoid PendingDeprecationWarning."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=PendingDeprecationWarning)
        return TagNode.parse(source, parser_options=parser_options)
