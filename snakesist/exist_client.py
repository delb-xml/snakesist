"""
.. module:: exist_client
    :synopsis: A module containing basic tools for connecting to eXist.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, NamedTuple
from urllib.parse import urljoin
from uuid import uuid4

import delb
import requests
from lxml import etree  # type: ignore
from requests.auth import HTTPBasicAuth

from snakesist.errors import ExistAPIError


QueryResultItem = NamedTuple(
    "QueryResultItem",
    [("absolute_id", str), ("node_id", str), ("document_path", str), ("node", delb.NodeBase)]
)


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8080
DEFAULT_USER = "admin"
DEFAULT_PASSWORD = ""
DEFAULT_PARSER = etree.XMLParser(recover=True)


class Resource(ABC):
    """
    A representation of an eXist resource (documents, nodes etc.).
    Each Resource object must be coupled to an :class:`ExistClient`.

    Resources are identified by IDs: Some resources (documents) just have
    an absolute resource ID, while others (nodes) require an additional node ID.
    """

    def __init__(
            self,
            exist_client: "ExistClient",
            query_result: Optional[QueryResultItem] = None
    ):
        """
        :param exist_client: The client to which the resource is coupled.
        :query_result: A tuple containing the absolute resource ID, node ID
                       and the node of the resource.
        """
        self.node: Optional[delb.NodeBase]

        self._exist_client = exist_client

        if query_result:
            self._abs_resource_id, self._node_id, self._document_path, self.node = query_result
        else:
            self._abs_resource_id = self._node_id = ""
            self.node = None
            self._document_path = ''

    def __str__(self):
        return str(self.node)

    def update_pull(self):
        """
        Retrieve the current node state from the database and update the object.
        """
        self.node = self._exist_client.retrieve_resource(
            abs_resource_id=self._abs_resource_id, node_id=self._node_id
        )

    @abstractmethod
    def update_push(self):
        """
        Write the resource object to the database.
        """
        pass

    @abstractmethod
    def delete(self):
        """
        Remove the node from the database.
        """
        pass

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


class DocumentResource(Resource):
    """
    A representation of an eXist document node
    """

    def delete(self):
        self._exist_client.delete_document(document_path=self.document_path)
        self._node_id = ""
        self._abs_resource_id = ""
        self._document_path = ""

    def update_push(self):
        self._exist_client.update_document(
            data=str(self.node),
            document_path=self.document_path,
        )


class NodeResource(Resource):
    """
    A representation of an eXist node at the sub-document level
    """

    def delete(self):
        self._exist_client.delete_node(
            abs_resource_id=self._abs_resource_id, node_id=self._node_id
        )
        self._node_id = ""
        self._abs_resource_id = ""

    def update_push(self):
        self._exist_client.update_node(
            data=str(self.node),
            abs_resource_id=self._abs_resource_id,
            node_id=self._node_id,
        )


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
    :param parser: an lxml etree.XMLParser instance to parse query results
    """

    def __init__(
            self,
            host: str = DEFAULT_HOST,
            port: int = DEFAULT_PORT,
            user: str = DEFAULT_USER,
            password: str = DEFAULT_PASSWORD,
            prefix: str = "exist",
            parser: etree.XMLParser = DEFAULT_PARSER
    ):
        self._root_collection = "/"
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.prefix = prefix
        self.parser = parser

    @staticmethod
    def _join_paths(*args):
        return "/".join(s.strip("/") for s in args)

    def _get_request(self, url: str, query: Optional[str] = None, wrap: bool = True) -> bytes:
        if query:
            params = {
                "_howmany": "0", "_indent": "no",
                "_wrap": "yes" if wrap else "no", "_query": query
            }
        else:
            params = {}

        response = requests.get(
            url,
            headers={"Content-Type": "application/xml"},
            auth=HTTPBasicAuth(self.user, self.password),
            params=params
        )

        response.raise_for_status()

        return response.content

    def _put_request(self, url: str, data: str) -> bytes:
        response = requests.put(
            url,
            headers={"Content-Type": "application/xml"},
            auth=HTTPBasicAuth(self.user, self.password),
            data=data.encode("utf-8")
        )

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        return response.content

    def _delete_request(self, url: str) -> None:
        response = requests.delete(
            url,
            headers={"Content-Type": "application/xml"},
            auth=HTTPBasicAuth(self.user, self.password),
        )

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

    @staticmethod
    def _parse_item(node: delb.TagNode) -> QueryResultItem:
        content_node = node.first_child
        assert isinstance(content_node, delb.TagNode)
        return QueryResultItem(
            node["absid"], node["nodeid"],
            node["path"], content_node.detach()
        )

    @property
    def base_url(self) -> str:
        """
        The base URL pointing to the eXist instance.
        """
        return f"http://{self.host}:{self.port}/{self.prefix}/"

    @property
    def root_collection(self) -> str:
        """
        The configured root collection for database queries.
        """
        return self._root_collection

    @root_collection.setter
    def root_collection(self, collection: str):
        """
        Set the path to the root collection for database
        queries (e. g. '/db/foo/bar/').
        """

        self._root_collection = collection

    @property
    def root_collection_url(self):
        """
        The URL pointing to the configured root collection.
        """

        data_path = self._join_paths("/rest/", self.root_collection)
        url = urljoin(self.base_url, data_path)
        return url

    def query(self, query_expression: str) -> delb.Document:
        """
        Make a database query using XQuery

        :param query_expression: XQuery expression
        :return: The query result as a ``delb.Document`` object.
        """
        response_string = self._get_request(
            self.root_collection_url, query=query_expression
        )
        return delb.Document(response_string, self.parser)

    def create_resource(self, document_path: str, node: str):
        """
        Write a new document node to the database.

        :param document_path: Path to collection where document will be stored,
                                relative to the configured root collection
        :param node: XML string
        """
        path = self._join_paths(self.root_collection, document_path)
        self.query(
            f"let $collection-check := if (not(xmldb:collection-available('{path}'))) "
            f"then (xmldb:create-collection('/', '{path}')) else () "
            f"return xmldb:store('/{path}', '{uuid4().hex}', {node})"
        )

    def retrieve_resources(self, xpath: str) -> List[Resource]:
        """
        Retrieve a set of resources from the database using
        an XPath expression.

        :param xpath: XPath expression (whatever version your eXist
                      instance supports via its RESTful API)
        :return: The query results as a list of :class:`Resource` objects.
        """
        results_node = self.query(
            f"for $node in {xpath} "
            f"return <pyexist-result "
            f"nodeid='{{util:node-id($node)}}' " 
            f"absid='{{util:absolute-resource-id($node)}}' "
            f"path='{{util:collection-name($node) || '/' || util:document-name($node)}}'>"
            f"{{$node}}</pyexist-result>"
        )
        resources = []
        for item in results_node.css_select("pyexist-result"):
            query_result = self._parse_item(item)
            resources.append(
                DocumentResource(exist_client=self, query_result=query_result)
                if query_result.node_id == "1"
                else NodeResource(exist_client=self, query_result=query_result)
            )
        return resources

    def retrieve_resource(
        self, abs_resource_id: str, node_id: str = ""
    ) -> Resource:
        """
        Retrieve a single resource by its internal database IDs.

        :param abs_resource_id: The absolute resource ID pointing to the document.
        :param node_id: The node ID locating a node inside a document (optional).
        :return: The queried node as a ``Resource`` object.
        """
        path = self.query(
            f"let $node := util:get-resource-by-absolute-id({abs_resource_id})"
            f"return util:collection-name($node) || '/' || util:document-name($node)"
        ).root.full_text
        if node_id:
            return NodeResource(
                self, QueryResultItem(
                    abs_resource_id,
                    node_id,
                    path,
                    self.query(
                        f"util:node-by-id(util:get-resource-by-absolute-id({abs_resource_id}), '{node_id}')"
                    ).root.first_child.detach()
                )
            )
        else:
            return DocumentResource(
                self, QueryResultItem(
                    abs_resource_id,
                    node_id,
                    path,
                    self.query(
                        f"util:get-resource-by-absolute-id({abs_resource_id})"
                    ).root.first_child.detach()
                )
            )

    def update_node(
        self, data: str, abs_resource_id: str, node_id: str
    ) -> None:
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

    def update_document(
        self, data: str, document_path: str
    ) -> None:
        """
        Replace a document root node with an updated version.

        :param data: A well-formed XML string containing the node to replace the old one with.
        :param document_path: The path pointing to the document (relative to the REST endpoint, e. g. '/db/foo/bar')
        """
        url = self._join_paths(self.base_url, "rest", document_path)
        self._put_request(url, data)

    def delete_node(
            self, abs_resource_id: str, node_id: str = ""
    ) -> None:
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
        Remove a document from a database.

        :param document_path: The path pointing to the document (relative to the REST endpoint, e. g. '/db/foo/bar')
        """
        url = self._join_paths(self.base_url, "rest", document_path)
        self._delete_request(url)
