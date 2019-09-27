"""
.. module:: exist_client
    :synopsis: A module containing basic tools for connecting to eXist.
"""

from urllib.parse import urljoin
from typing import List, Optional, Tuple

import delb
import requests
from abc import ABC
from lxml import etree  # type: ignore
from uuid import uuid4
from requests.auth import HTTPBasicAuth
from typing import NamedTuple
from requests.exceptions import HTTPError

from snakesist.errors import ExistAPIError


QueryResultItem = NamedTuple(
    "QueryResultItem",
    [("absolute_id", str), ("node_id", str), ("path", str), ("node", delb.TagNode)]
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
        self.node: Optional[delb.TagNode]

        self._exist_client = exist_client

        if query_result:
            self._abs_resource_id, self._node_id, self.path, self.node = query_result
        else:
            self._abs_resource_id = self._node_id = ""
            self.node = None
            self.path = None

    def __str__(self):
        return str(self.node)

    def update_pull(self):
        """
        Retrieve the current node state from the database and update the object.
        """
        self.node = self._exist_client.retrieve_resource(
            abs_resource_id=self._abs_resource_id, node_id=self._node_id
        )

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


class DocumentResource(Resource):
    """
    A representation of an eXist document node
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
        super().__init__(exist_client, query_result)

    def delete(self):
        """
        Remove the document from the database.
        """
        self._exist_client.delete_document(path=self.path)
        self._node_id = None
        self._abs_resource_id = None

    def update_push(self):
        """
        Write the resource object to the database.
        """
        self._exist_client.update_document(
            updated_node=str(self.node),
            path=self.path,
        )


class NodeResource(Resource):
    """
    A representation of an eXist node at the sub-document level
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
        super().__init__(exist_client, query_result)

    def delete(self):
        """
        Remove the node from the database.
        """
        self._exist_client.delete_node(
            abs_resource_id=self._abs_resource_id, node_id=self._node_id
        )
        self._node_id = None
        self._abs_resource_id = None

    def update_push(self):
        """
        Write the resource object to the database.
        """
        self._exist_client.update_node(
            updated_node=str(self.node),
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
            parser:etree.XMLParser = DEFAULT_PARSER
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
        if wrap:
            wrap_value = "yes"
        else:
            wrap_value = "no"
        if query:
            params = {"_howmany": "0", "_indent": "no", "_wrap": wrap_value, "_query": query}
        else:
            params = {}

        response = requests.get(
            url,
            headers={"Content-Type": "application/xml"},
            auth=HTTPBasicAuth(self.user, self.password),
            params=params
        )

        if response.status_code != requests.codes.ok:
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
        return node["absid"], node["nodeid"], node["path"], content_node.detach()

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
        :param parser: Parser used for processing XML
        :return: The query result as a ``delb.Document`` object.
        """
        response_string = self._get_request(
            self.root_collection_url, query=query_expression
        )
        return delb.Document(response_string, self.parser)

    def create_resource(self, collection_path: str, node: str):
        """
        Write a new document node to the database.

        :param collection_path: Path to collection where document will be stored,
                                relative to the configured root collection
        :param node: XML string
        """
        path = self._join_paths(self.root_collection, collection_path)
        xq = (
            f"let $collection-check := if (not(xmldb:collection-available('{path}'))) "
            f"then (xmldb:create-collection('/', '{path}')) else () "
            f"return xmldb:store('/{path}', '{uuid4().hex}', {node})"
        )
        self.query(xq)

    def retrieve_resources(self, xpath: str) -> List[Resource]:
        """
        Retrieve a set of resources from the database using
        an XPath expression.

        :param xpath: XPath expression (whatever version your eXist
                      instance supports via its RESTful API)
        :return: The query results as a list of :class:`Resource` objects.
        """
        xq = (
            f"for $node in {xpath} "
            f"return <pyexist-result "
            f"nodeid='{{util:node-id($node)}}' " 
            f"absid='{{util:absolute-resource-id($node)}}' "
            f"path='{{util:collection-name($node) || '/' || util:document-name($node)}}'>"
            f"{{$node}}</pyexist-result>"
        )
        results_node = self.query(xq)
        resources = []
        for item in results_node.css_select("pyexist-result"):
            query_result = self._parse_item(item)
            if query_result.node_id == "1":
                resource = DocumentResource(exist_client=self, query_result=query_result)
            else:
                resource = NodeResource(exist_client=self, query_result=query_result)
            resources.append(resource)
        return resources

    def retrieve_resource(
        self, abs_resource_id: str, node_id: str = ""
    ) -> Resource:
        """
        Retrieve a single resource by its internal database IDs.

        :param abs_resource_id: The absolute resource ID pointing to the document.
        :param node_id: The node ID locating a node inside a document (optional).
        :return: The queried node as a ``delb.TagNode`` object.
        """
        if node_id:
            result_node = self.query(
                query_expression=f"""util:node-by-id(
                    util:get-resource-by-absolute-id({abs_resource_id}), '{node_id}')"""
            )
        else:
            result_node = self.query(
                query_expression=f"util:get-resource-by-absolute-id({abs_resource_id})"
            )
        return result_node.xpath("./*")[0].detach()  # TODO: Performance check?

    def update_resource(
        self, updated_node: str, abs_resource_id: str, node_id: str = ""
    ) -> None:
        """
        Replace a database resource with an updated one.

        :param abs_resource_id: The absolute resource ID pointing to the document.
        :param node_id: The node ID locating a node inside a document (optional).
        """
        if node_id:
            self.query(
                query_expression=f"""
                let $node := util:node-by-id(
                util:get-resource-by-absolute-id({abs_resource_id}), '{node_id}')
                return update replace $node with {updated_node}"""
            )
        else:
            self.query(
                query_expression=f"""
                let $node := util:get-resource-by-absolute-id({abs_resource_id})
                return update replace $node with {updated_node}"""
            )

    def update_node(
        self, updated_node: str, abs_resource_id: str, node_id: str
    ) -> None:
        """
        Replace a sub-document node with an updated version.

        :param updated_node: The node to replace the old one with.
        :param abs_resource_id: The absolute resource ID pointing to the document containing the node.
        :param node_id: The node ID locating the node inside the containing document.
        """
        xq = (
            f"update replace util:node-by-id(util:get-resource-by-absolute-id({abs_resource_id}), '{node_id}')"
            f"with {updated_node}"
        )
        self.query(xq)

    def update_document(
        self, updated_node: str, path: str
    ) -> None:
        """
        Replace a document root node with an updated version.

        :param updated_node: The node to replace the old one with.
        :param path: The path pointing to the document (relative to the REST endpoint, e. g. '/db/foo/bar')
        """
        url = self._join_paths(self.base_url, "rest", path)
        self._put_request(url, updated_node)

    def delete_node(
            self, abs_resource_id: str, node_id: str = ""
    ) -> None:
        """
        Remove a node from the database.

        :param abs_resource_id: The absolute resource ID pointing to the document.
        :param node_id: The node ID locating a node inside a document (optional).
        """
        xq = (
             f"let $node := util:node-by-id("
             f"util:get-resource-by-absolute-id({abs_resource_id}), '{node_id}')"
             f"return update delete $node"
        )
        self.query(xq)

    def delete_document(self, path: str) -> None:
        """
        Remove a document from a database.

        :param path: The path pointing to the document (relative to the REST endpoint, e. g. '/db/foo/bar')
        """
        url = self._join_paths(self.base_url, "rest", path)
        self._delete_request(url)
