import re
from functools import wraps
from pathlib import PurePosixPath
from types import SimpleNamespace
from typing import Any, Dict
from urllib.parse import urlparse
from warnings import warn

import httpx
from _delb.plugins import plugin_manager, DocumentMixinBase
from _delb.plugins.https_loader import https_loader
from _delb.typing import LoaderResult
from lxml import etree

from snakesist.exceptions import (
    SnakesistConfigError,
    SnakesistWriteError,
    SnakesistReadError,
    SnakesistNotFound,
)
from snakesist.exist_client import _mangle_path, _validate_filename, ExistClient


is_existdb_url = re.compile(r"^existdb(\+https?)?://.+").match


@plugin_manager.register_loader()
def existdb_loader(source: Any, config: SimpleNamespace) -> LoaderResult:
    """
    This loader loads a document from a eXist-db instance. There are two ways to
    retrieve a particular document.

    One is to specify an URL with the ``existdb://`` scheme, which can optionally be
    extended with the transport protocol: ``existdb+http://`` or ``existdb+https://``.

    The overall pattern of the URLs is:
    ``existdb[+http[s]]://[[<username>]:[<password>]@]<host>[:<port>][/<prefix>]/<path>``

    For example:

    .. code-block:: python

        document = delb.Document("existdb://example.org/exist/corpus/document.xml")

    Note that omitted ports would default to ``80`` or ``443`` respectively, depending
    on the used transport protocol. Which in turn is probed for if not specified,
    preferring encrypted connections.

    The other way is to pass a configured client as ``existdb_client`` keyword and a
    path as string or :class:`pathlib.PurePosixPath` that points to the document within
    the client's configured :attr:`snakesist.ExistClient.root_collection`, hence this
    would be an equivalent to the example above, assuming that ``https`` is available on
    the addressed host:

    .. code-block:: python

        client = snakesist.ExistClient(
            transport="https",
            host="example.org",
            port=443,
            user="",
            root_collection="/corpus",
        )
        document = delb.Document("document.xml", existdb_client=client)

    In both cases the document instance will have a configured ``config`` namespace
    ``existdb`` with the property ``client`` which is a :class:`snakesist.ExistClient`
    instance.

    Further interaction with the database is facilitated with the
    :class:`ExistDBExtension` that extends the :class:`delb.Document` class.
    """
    if isinstance(source, str) and is_existdb_url(source):
        return load_from_url(source, config)
    elif hasattr(config, "existdb"):
        return load_from_path(source, config)
    else:
        return (
            "The input value is neither a existdb URL nor is a existdb client "
            "configured."
        )


def load_from_url(source: Any, config: SimpleNamespace) -> LoaderResult:
    if hasattr(config, "existdb"):
        warn("The current existdb configuration is replaced.")
    config.existdb = SimpleNamespace(client=ExistClient.from_url(source))
    path = PurePosixPath(urlparse(source).path).relative_to(
        PurePosixPath(f"/{config.existdb.client.prefix}")
    )
    result = load_from_path(path, config)
    if isinstance(result, etree._ElementTree):
        config.source_url = source
    return result


def load_from_path(source: Any, config: SimpleNamespace) -> LoaderResult:
    path = _mangle_path(source) if isinstance(source, str) else source
    if not isinstance(path, PurePosixPath):
        raise TypeError

    client: ExistClient = config.existdb.client
    url = f"{client.root_collection_url}/{path}"

    try:
        result = https_loader(url, config, client=client.http_client)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise SnakesistNotFound(f"Document '{path}' not found.")
        raise SnakesistReadError("Could not read from database.") from e

    config.__dict__.pop("source_url", None)
    config.existdb.collection = path.parent
    config.existdb.filename = path.name
    return result


def ensure_configured_client(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not isinstance(self.config.existdb.client, ExistClient):
            raise SnakesistConfigError(
                f"The document {self!r} has no configured eXist-db client."
            )
        return method(self, *args, **kwargs)

    return wrapper


class ExistDBExtension(DocumentMixinBase):
    """
    This class provides extensions to :class:`delb.Document` in order to interact
    with a eXist-db instance.

    See :func:`existdb_loader` on retrieving documents from an eXist-db instance.
    """

    config: SimpleNamespace

    @classmethod
    def _init_config(cls, config: SimpleNamespace, kwargs: Dict[str, Any]):
        client = kwargs.pop("existdb_client", None)
        if not (client is None or isinstance(client, ExistClient)):
            raise ValueError("Invalid object passed as existdb_client.")
        config.existdb = SimpleNamespace(
            client=client, collection=PurePosixPath("."), filename=""
        )
        super()._init_config(config, kwargs)

    @property
    def existdb_collection(self) -> str:
        """
        The collection within an eXist-db instance where the document was fetched from.
        This property can be changed to designate another location to store to.
        """
        return f"/{self.config.existdb.collection}"

    @existdb_collection.setter
    def existdb_collection(self, path: str):
        self.config.existdb.collection = _mangle_path(path)

    @ensure_configured_client
    def existdb_delete(self):
        """
        Deletes the document that currently resides at the location which is made up of
        the current :attr:`ExistDBExtension.existdb_collection` and
        :attr:`ExistDBExtension.existdb_filename` in the associated eXist-db instance.
        """
        self.config.existdb.client.delete_document(
            f"{self.existdb_collection}/{self.existdb_filename}"
        )

    @property
    def existdb_filename(self) -> str:
        """
        The filename within the eXist-db instance and collection where the document was
        fetched from.
        This property can be changed to designate another location to store to.
        """
        return self.config.existdb.filename

    @existdb_filename.setter
    def existdb_filename(self, filename: str):
        _validate_filename(filename)
        self.config.existdb.filename = filename

    @ensure_configured_client
    def existdb_store(
        self,
        collection: str = None,
        filename: str = None,
        replace_existing: bool = False,
    ):
        """
        Stores the current state of the document in the associated eXist-db instance.

        :param collection: An alternate collection to save into.
        :param filename: An alternate name to store the document.
        :param replace_existing: Allows to overwrite existing documents.
        """

        client = self.config.existdb.client
        if collection is None:
            collection = self.existdb_collection
        else:
            collection = str(_mangle_path(collection))
        if filename is None:
            filename = self.existdb_filename
        else:
            _validate_filename(filename)

        http_client = self.config.existdb.client.http_client
        url = f"{client.root_collection_url}/{collection}/{filename}"

        if not replace_existing and http_client.head(url).status_code == 200:
            raise SnakesistWriteError(
                "Document already exists. Overwriting must be allowed explicitly."
            )

        response = http_client.put(
            url,
            headers={"Content-Type": "application/xml"},
            content=str(self),
        )
        try:
            response.raise_for_status()
        except Exception as e:
            raise SnakesistWriteError("Unhandled error while storing.") from e
        if not response.status_code == 201:
            raise SnakesistWriteError(f"Unexpected response: {response}")
