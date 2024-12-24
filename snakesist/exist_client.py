"""
.. module:: exist_client
    :synopsis: A module containing basic tools for connecting to eXist.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from string import Template
from typing import Any, Final, NamedTuple, Optional
from urllib.parse import urlparse

import httpx
from _delb.nodes import NodeBase, TagNode
from _delb.parser import ParserOptions

from snakesist.exceptions import (
    SnakesistConfigError,
    SnakesistNotFound,
    SnakesistQueryError,
    SnakesistReadError,
    SnakesistWriteError,
)


class QueryResultItem(NamedTuple):
    absolute_id: str
    node_id: str
    document_path: str
    node: NodeBase


class QueryTemplate(Template):
    delimiter = "@"


class ConnectionProps(NamedTuple):
    transport: str
    user: str
    password: str
    host: str
    port: int
    prefix: PurePosixPath


DEFAULT_TRANSPORT: Final = "http"
DEFAULT_HOST: Final = "localhost"
DEFAULT_PORT: Final = 8080
DEFAULT_USER: Final = "admin"
DEFAULT_PASSWORD: Final = ""
EXISTDB_NAMESPACE: Final = "http://exist.sourceforge.net/NS/exist"
SNAKESIST_NAMESPACE: Final = "https://snakesist.readthedocs.io/"
TRANSPORT_PROTOCOLS: Final = {"https": 443, "http": 80}  # the order matters!


PATH_OF_ABS_ID_QUERY: Final = QueryTemplate(
    """\
let $node := util:get-resource-by-absolute-id(@id)
return util:collection-name($node) || "/" || util:document-name($node)
"""
)

RETRIEVE_NODE_QUERY = QueryTemplate(
    """\
util:node-by-id(util:get-resource-by-absolute-id(@abs_resource_id), "@node_id")"""
)


XPATH_QUERY: Final = QueryTemplate(
    """\
for $node in @expression return
<snakesist:result xmlns:snakesist="SNAKESIST_NAMESPACE"
  snakesist:nodeid="{util:node-id($node)}"
  snakesist:absid="{util:absolute-resource-id($node)}"
  snakesist:path="{util:collection-name($node) || "/" || util:document-name($node)}"
>{$node}</snakesist:result>
""".replace(
        "SNAKESIST_NAMESPACE", SNAKESIST_NAMESPACE
    )
)


XQUERY_PAYLOAD: Final = QueryTemplate(
    """\
<query xmlns="EXISTDB_NAMESPACE" start="1" max="0" cache="no">
  <text><![CDATA[@query]]></text>
  <properties>
    <property name="indent" value="no"/>
    <property name="wrap" value="yes"/>
  </properties>
</query>
""".replace(
        "EXISTDB_NAMESPACE", EXISTDB_NAMESPACE
    )
)


content_type_is_xml: Final = re.compile(r"^(application|text)/xml(;.+)?").match


def _mangle_path(path: str) -> PurePosixPath:
    return PurePosixPath(path.lstrip("/"))


def _validate_filename(filename: str):
    as_path = PurePosixPath(filename)
    if str(as_path) != as_path.name:
        raise ValueError(f"Invalid filename: '{filename}'")


class NodeResource:
    """
    A representation of an XML node in a eXist-db resource.
    Each Resource object must be coupled to an :class:`ExistClient`.

    Resources are identified by an absolute resource ID that points to the containing
    document and a node ID within that document.

    :param exist_client: The client to which the resource is coupled.
    :query_result: A tuple containing the absolute resource ID, node ID
                   and the node of the resource.

    """

    def __init__(
        self,
        exist_client: "ExistClient",
        query_result: QueryResultItem,
    ):
        self._abs_resource_id = query_result.absolute_id
        self._document_path = query_result.document_path
        self._exist_client = exist_client
        self.node = query_result.node
        self._node_id = query_result.node_id

    def __str__(self):
        return str(self.node)

    def update_pull(self):
        """
        Retrieve the current node state from the database and update the object.
        """
        self.node = self._exist_client.retrieve_resource(
            abs_resource_id=self._abs_resource_id, node_id=self._node_id
        )

    def update_push(self):
        """Writes the node to the database."""
        self._exist_client.update_node(
            data=str(self.node),
            abs_resource_id=self._abs_resource_id,
            node_id=self._node_id,
        )

    def delete(self):
        """Deletes the node from the database."""
        self._exist_client.delete_node(
            abs_resource_id=self._abs_resource_id, node_id=self._node_id
        )
        self._node_id = ""
        self._abs_resource_id = ""

    @property
    def abs_resource_id(self):
        """
        The absolute resource ID pointing to a document in the database.
        """
        return self._abs_resource_id

    @property
    def node_id(self):
        """
        The node ID locating the node relative to the containing document.
        """
        return self._node_id

    @property
    def document_path(self):
        """
        The resource path pointing to the document.
        """
        return self._document_path


class ExistClient:
    """
    An eXist-db client object representing a database instance.
    The client can be used for CRUD operations.
    Resources can be queried using an XPath expression.
    Queried resources are identified by the absolute resource ID and,
    if the resource is part of a document, the node ID.

    :param host: hostname
    :param port: port used to connect to the configured eXist instance
    :param user: username
    :param password: password
    :param prefix: configured path prefix for the eXist instance
    :param root_collection: a path to a collection which will be used as root for all
                            document paths
    :param parser: deprecated
    :param parser_options: a named tuple from delb to define the XML parser's behaviour
    """

    def __init__(
        self,
        transport: str = DEFAULT_TRANSPORT,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        user: str = DEFAULT_USER,
        password: str = DEFAULT_PASSWORD,
        prefix: str = "exist",
        root_collection: str = "/",
        parser: Any = None,  # REMOVE eventually
        parser_options: Optional[ParserOptions] = None,
    ):
        if parser is not None:
            raise ValueError(
                "The parsers argument isn't used anymore. Parsers are derived from the"
                "provided `parser_options`."
            )
        _prefix = _mangle_path(prefix)
        self.__connection_props = ConnectionProps(
            transport=transport,
            user=user,
            password=password,
            host=host,
            port=port,
            prefix=_prefix,
        )
        self.__base_url = f"{transport}://{user}:{password}@{host}:{port}/{_prefix}"
        self.http_client = httpx.Client(http2=True)
        self.parser_options = parser_options or ParserOptions(reduce_whitespace=True)
        self.root_collection = root_collection

    @classmethod
    def from_url(
        cls,
        url: str,
        parser=None,  # REMOVE eventually
        parser_options: Optional[ParserOptions] = None,
    ) -> "ExistClient":
        """
        Returns a client instance from the given URL. Path parts that point to something
        beyond the database instance's path prefix are ignored.
        """
        parsed_url = urlparse(url)

        if parsed_url.scheme == "existdb":
            transport = None
        elif parsed_url.scheme.startswith("existdb+"):
            transport = parsed_url.scheme.split("+")[1]
            if transport not in TRANSPORT_PROTOCOLS:
                raise SnakesistConfigError(
                    f"Invalid transport '{transport}' for existdb."
                )
        else:
            raise SnakesistConfigError(
                f"Invalid URL scheme '{parsed_url.scheme}' for existdb."
            )

        user = parsed_url.username or ""
        password = parsed_url.password or ""
        host = parsed_url.hostname
        assert host is not None
        port = parsed_url.port

        if not isinstance(host, str) and host:
            raise SnakesistConfigError(f"Invalid host in URL: {host}")

        if transport is None:
            probe_result = cls._probe_transport_and_port(
                f"{user}:{password}@{host}", port
            )
            if probe_result is None:
                raise SnakesistConfigError(
                    f"Couldn't figure out how to talk to {host}."
                )
            transport, port = probe_result
        elif port is None:
            port = TRANSPORT_PROTOCOLS[transport]

        prefix = cls._probe_instance_prefix(
            f"{transport}://{user}:{password}@{host}:{port}", parsed_url.path
        )
        if prefix is None:
            raise SnakesistConfigError(
                "Couldn't determine the location of the 'rest' interface."
            )

        return cls(
            transport=transport,
            host=host,
            port=port,
            user=user,
            password=password,
            prefix=prefix,
            parser=parser,
            parser_options=parser_options,
        )

    @staticmethod
    def _probe_transport_and_port(
        host: str, port: Optional[int]
    ) -> tuple[str, int] | None:
        for transport, default_port in TRANSPORT_PROTOCOLS.items():
            _port = port or default_port
            try:
                httpx.head(f"{transport}://{host}:{_port}/")
            except httpx.TransportError:
                pass
            else:
                return transport, _port
        return None

    @staticmethod
    def _probe_instance_prefix(base: str, path: str) -> Optional[str]:
        path_parts = PurePosixPath(path).parts[1:]
        encountered_collection = False

        # looks for longest path as different instances could have overlapping prefixes
        # will return false results if a path contained a part named "rest"
        for i in range(len(path_parts), 0, -1):
            response = httpx.get(f"{base}/{'/'.join(path_parts[:i])}/rest/")

            if response.status_code == 401:
                raise SnakesistConfigError("Failed authentication.")

            if not content_type_is_xml(response.headers.get("Content-Type", "")):
                if encountered_collection:
                    break
                else:
                    continue

            parsed_response = TagNode.parse(response.content)
            if (
                parsed_response.namespace == EXISTDB_NAMESPACE
                and parsed_response.local_name == "result"
            ):
                encountered_collection = True
            elif encountered_collection:
                break

        if encountered_collection:
            return "/".join(path_parts[:i])
        else:
            return None

    @property
    def base_url(self) -> str:
        """
        The base URL pointing to the eXist instance.
        """
        return self.__base_url

    @property
    def transport(self) -> str:
        """
        The used transport protocol
        """
        return self.__connection_props.transport

    @property
    def host(self) -> str:
        """
        The database hostname
        """
        return self.__connection_props.host

    @property
    def port(self) -> int:
        """
        The database port number
        """
        return self.__connection_props.port

    @property
    def user(self) -> str:
        """
        The user name used to connect to the database
        """
        return self.__connection_props.user

    @property
    def password(self) -> str:
        """
        The password used to connect to the database
        """
        return self.__connection_props.password

    @property
    def prefix(self) -> str:
        """
        The URL prefix of the database
        """
        return str(self.__connection_props.prefix)

    @property
    def root_collection(self) -> str:
        """
        The configured root collection for database queries.
        """
        return str(self.__root_collection)

    @root_collection.setter
    def root_collection(self, path: str):
        """
        Set the path to the root collection for database
        queries (e. g. '/db/foo/bar/').
        """
        self.__root_collection = _mangle_path(path)

    @property
    def root_collection_url(self) -> str:
        """
        The URL pointing to the configured root collection.
        """
        result = f"{self.__base_url}/rest/{self.__root_collection}"
        if result.endswith("/."):
            return result[:-2]
        else:
            return result

    def query(self, query_expression: str) -> TagNode:
        """
        Make a database query using XQuery. The configured root collection
        will be the starting point of the query.

        :param query_expression: XQuery expression
        :return: The query result as a :class:`delb.TagNode` object.
        """
        payload = XQUERY_PAYLOAD.substitute(query=query_expression)
        response = self.http_client.post(
            self.root_collection_url,
            headers={"Content-Type": "application/xml"},
            content=payload,
        )

        if response.status_code == 400:
            raise SnakesistQueryError(payload, response)

        try:
            response.raise_for_status()
        except Exception as e:
            raise SnakesistReadError("Unhandled query error.") from e

        return TagNode.parse(response.content, parser_options=self.parser_options)

    def xpath(self, expression: str) -> list[NodeResource]:
        """
        Retrieve a set of resources from the database using
        an XPath expression. The configured root collection
        will be the starting point of the query.

        :param expression: XPath expression (whatever version your eXist
                           instance supports via its RESTful API)
        :return: The query results as a list of :class:`NodeResource` objects.
        """
        results_node = self.query(XPATH_QUERY.substitute(expression=expression))
        assert results_node.namespace == EXISTDB_NAMESPACE
        assert results_node.local_name == "result"
        resources = []
        for result_node in results_node.xpath(
            "//result", namespaces={None: SNAKESIST_NAMESPACE}
        ):
            assert isinstance(result_node, TagNode)
            content_node = result_node[0]
            assert isinstance(content_node, NodeBase)
            query_result = QueryResultItem(
                absolute_id=result_node["absid"].value,
                node_id=result_node["nodeid"].value,
                document_path=result_node["path"].value,
                node=content_node.detach(),
            )
            resources.append(NodeResource(exist_client=self, query_result=query_result))
        return resources

    # TODO? rename
    def retrieve_resource(self, abs_resource_id: str, node_id: str) -> NodeResource:
        """
        Retrieve a single resource by its internal database IDs.

        :param abs_resource_id: The absolute resource ID pointing to the document.
        :param node_id: The node ID locating a node inside a document (optional).
        :return: The queried node as a ``Resource`` object.
        """
        queried_node = self.query(
            RETRIEVE_NODE_QUERY.substitute(
                abs_resource_id=abs_resource_id, node_id=node_id
            )
        )[0]
        assert isinstance(queried_node, TagNode)

        return NodeResource(
            self,
            QueryResultItem(
                absolute_id=abs_resource_id,
                node_id=node_id,
                document_path=self._get_document_path_of_node(abs_resource_id),
                node=queried_node.detach(),
            ),
        )

    def _get_document_path_of_node(self, abs_resource_id: str) -> str:
        result_node = (
            self.query(PATH_OF_ABS_ID_QUERY.substitute(id=abs_resource_id))
            .xpath("//result/value", namespaces={None: EXISTDB_NAMESPACE})
            .first
        )
        assert isinstance(result_node, TagNode)
        path = result_node.full_text
        return path

    def update_node(self, data: str, abs_resource_id: str, node_id: str) -> None:
        """
        Replace a sub-document node with an updated version.

        :param data: A well-formed XML string containing the node to replace the old one with.
        :param abs_resource_id: The absolute resource ID pointing to the document containing the node.
        :param node_id: The node ID locating the node inside the containing document.
        """
        self.query(
            f"update replace util:node-by-id(util:get-resource-by-absolute-id({abs_resource_id}), '{node_id}')"
            f"with {data}"
        )

    def delete_node(self, abs_resource_id: str, node_id: str = "") -> None:
        """
        Remove a node from the database.

        :param abs_resource_id: The absolute resource ID pointing to the document.
        :param node_id: The node ID locating a node inside a document (optional).
        """
        self.query(
            f"let $node := util:node-by-id("
            f"util:get-resource-by-absolute-id({abs_resource_id}), '{node_id}')"
            f"return update delete $node"
        )

    def delete_document(self, document_path: str) -> None:
        """
        Removes a document from the associated database.

        :param document_path: The path pointing to the document within the root
                              collection.
        """
        response = self.http_client.delete(
            f"{self.root_collection_url}/{_mangle_path(document_path)}"
        )
        if response.status_code == 404:
            raise SnakesistNotFound(f"Document '{document_path}' not found.")
        try:
            response.raise_for_status()
        except Exception as e:
            raise SnakesistWriteError("Unhandled error while deleting.") from e
