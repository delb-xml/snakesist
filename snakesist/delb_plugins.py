from types import SimpleNamespace
from typing import Any, Dict

from delb.plugins import plugin_manager, DocumentExtensionHooks
from delb.typing import LoaderResult


@plugin_manager.register_loader()
def existdb_loader(source: Any, config: SimpleNamespace) -> LoaderResult:
    raise NotImplemented


@plugin_manager.register_document_extension
class ExistDBExtension(DocumentExtensionHooks):
    """
    This class provides extensions to :class:`delb.Document` in order to interact
    with a eXist-db instance.

    Documents can be loaded from an eXist-db instance by either specifying an URL with
    the ``existdb://`` scheme or by specifying a path made up of a collection path and
    a filename and passing a :class:`snakesist.ExistClient` instance with the
    ``existdb_client`` keyword. These two initializations would yield the same
    :class:`delb.Document`:

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
            prefix="exist",
        )
        document = delb.Document("/collection/document.xml", existdb_client=client)
    """

    def _init_config(self, config_args: Dict[str, Any]):
        raise NotImplemented
        super()._init_config(config_args)

    @property
    def existdb_collection(self):
        """
        The collection within an eXist-db instance where the document was fetched from.
        This property can be changed to designate another location to store to.
        """
        raise NotImplemented

    @existdb_collection.setter
    def existdb_collection(self, collection: str):
        raise NotImplemented

    def existdb_delete(self):
        """
        Deletes the document that currently resides at the location which is made up of
        the current ``existdb_collection`` and ``existdb_filename`` in the associated
        eXist-db instance.
        """
        raise NotImplemented

    @property
    def existdb_filename(self):
        """
        The filename within the eXist-db instance and collection where the document was
        fetched from.
        This property can be changed to designate another location to store to.
        """
        raise NotImplemented

    @existdb_filename.setter
    def existdb_filename(self, filename: str):
        raise NotImplemented

    def existdb_store(self, collection: str = None, filename: str = None):
        """
        Stores the current state of the document in the associated eXist-db instance.

        :param collection: An alternate collection to save into.
        :param filename: An alternate name to store the document.
        """
        raise NotImplemented
