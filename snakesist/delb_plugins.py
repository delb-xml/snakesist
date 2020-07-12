import re
from functools import wraps
from pathlib import PurePosixPath
from types import SimpleNamespace
from typing import Any, Dict
from urllib.parse import urlparse
from warnings import warn

import requests
from _delb.plugins import plugin_manager, DocumentExtensionHooks
from _delb.plugins.core_loaders import ftp_http_loader
from _delb.plugins.https_loader import https_loader
from _delb.typing import LoaderResult

from snakesist.exceptions import WriteError, ReadError, NotFound
from snakesist.exist_client import _mangle_path, _validate_filename, ExistClient


is_existdb_url = re.compile(r"^existdb(\+https?)?://.+").match


@plugin_manager.register_loader()
def existdb_loader(source: Any, config: SimpleNamespace) -> LoaderResult:
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
        warn("The configured existdb configuration is replaced.")
    # TODO return some exception messages as text
    config.existdb = SimpleNamespace(client=ExistClient.from_url(source))
    path = PurePosixPath(urlparse(source).path).relative_to(
        PurePosixPath(f"/{config.existdb.client.prefix}")
    )
    result = load_from_path(path, config)
    if isinstance(result, tuple):
        config.source_url = source
    return result


def load_from_path(source: Any, config: SimpleNamespace) -> LoaderResult:
    try:
        if isinstance(source, str):
            source = _mangle_path(source)
        if not isinstance(source, PurePosixPath):
            raise TypeError
    except Exception:
        return "The input value is not a proper path."
    else:
        path = source

    client: ExistClient = config.existdb.client
    url = f"{client.root_collection_url}/{path}"

    try:
        if client.transport == "https":
            result = https_loader(url, config)
        else:  # http
            result = ftp_http_loader(url, config)
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            raise NotFound(f"Document '{path}' not found.")
        raise ReadError("Could not read from database.")

    config.__dict__.pop("source_url", None)
    config.existdb.collection = path.parent
    config.existdb.filename = path.name
    return result


def ensure_configured_client(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not isinstance(self.config.existdb.client, ExistClient):
            raise RuntimeError(
                f"The document {self!r} has no configured eXist-db client."
            )
        return method(self, *args, **kwargs)

    return wrapper


@plugin_manager.register_document_extension
class ExistDBExtension(DocumentExtensionHooks):
    """
    This class provides extensions to :class:`delb.Document` in order to interact
    with a eXist-db instance.

    Documents can be loaded from an eXist-db instance by either specifying an URL with
    the ``existdb://`` scheme or by specifying a path made up of a collection path and
    a filename and passing a :class:`snakesist.ExistClient` instance with the
    ``existdb_client`` keyword. URL schemes can specify the desired transport
    protocol: ``existdb+http://`` or ``existdb+https://``. These two initializations
    would yield the same :class:`delb.Document`:

    .. code-block::

        import delb
        import snakesist

        # with an URL
        document = delb.Document(
            "existdb://example.exist-host.org/exist/collection/document.xml"
        )

        # with a client
        client = snakesist.ExistClient(
            host="example.exist-host.org",
            port=443,
            prefix="exist",
            root_collection="/",
        )
        document = delb.Document("/collection/document.xml", existdb_client=client)
    """

    # for mypy:
    config: SimpleNamespace

    def _init_config(self, config_args: Dict[str, Any]):
        client = config_args.pop("existdb_client", None)
        if not (client is None or isinstance(client, ExistClient)):
            raise ValueError("Invalid object passed as existdb_client.")
        self.config.existdb = SimpleNamespace(
            client=client, collection=PurePosixPath("."), filename=""
        )
        super()._init_config(config_args)

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
        the current ``existdb_collection`` and ``existdb_filename`` in the associated
        eXist-db instance.
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

        url = f"{client.root_collection_url}/{collection}/{filename}"

        if not replace_existing and requests.head(url).status_code == 200:
            raise WriteError(
                "Document already exists. Overwriting must be explicitly allowed."
            )

        response = requests.put(
            url, headers={"Content-Type": "application/xml"}, data=str(self).encode(),
        )
        if not response.status_code == 201:
            raise WriteError(f"Unexpected response: {response}")
        try:
            response.raise_for_status()
        except Exception as e:
            raise WriteError("Unhandled error while storing.") from e
