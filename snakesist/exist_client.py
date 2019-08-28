from datetime import datetime
startTime = datetime.now()

"""
Connector tools for eXist-db
"""

from snakesist.errors import ExistAPIError
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from lxml.etree import XMLSyntaxError
from lxml import etree
import requests
import delb


class Resource:
    """
    A representation of an eXist resource. Each Resource object is
    coupled to an ExistClient and can be updated or deleted.
    """

    def __init__(self, exist_client, query_result: tuple = None):
        if query_result:
            self._abs_resource_id = query_result[0]
            self._node_id = query_result[1]
            self._exist_client = exist_client
            if query_result[2]:
                self.node = query_result[2]
            else:
                self.node = None
        else:
            self._abs_resource_id = None
            self._node_id = None
            self.node = delb.TagNode()

    def __str__(self):
        return str(self.node)

    def update(self):
        self._exist_client.update_resource(
            updated_node=str(self.node),
            abs_resource_id=self._abs_resource_id,
            node_id=self._node_id,
        )

    def delete(self):
        self._exist_client.delete_resource(
            abs_resource_id=self._abs_resource_id, node_id=self._node_id
        )
        self._node_id = None
        self._abs_resource_id = None

    @property
    def abs_resource_id(self):
        return self._abs_resource_id

    @property
    def node_id(self):
        return self._node_id


class ExistClient:
    """
    An eXist-db client object which represents a database instance.
    The client can be used for CRUD operations. Resources can be queries
    using an XPath expression. Queried resources are identified by the absolute 
    resource ID and, if the resource is part of a document, the node id.
    """

    HOST = "localhost"
    PORT = 8080
    USR = "admin"
    PARSER = etree.XMLParser(recover=True)

    def __init__(self, host=HOST, port=PORT, usr=USR, pw="", prefix="exist"):
        """
        Initialize an eXist client object
        
        :param host: hostname of an eXist instance
        :param port: port used to connect to the configured eXist instance
        :param usr: username
        :param pw: password
        :param prefix: configured prefix for the eXist instance

        """

        self._root_collection = "/"
        self.host = host
        self.port = port
        self.usr = usr
        self.pw = pw
        self.prefix = prefix

    @staticmethod
    def _join_paths(*args):
        return "/".join(s.strip("/") for s in args)

    def _get_request(self, url, query=None):
        headers = {"Content-Type": "application/xml"}
        if query:
            params = {"_howmany": 0, "_indent": "no", "_query": query}
            req = requests.get(
                url,
                headers=headers,
                auth=HTTPBasicAuth(self.usr, self.pw),
                params=params,
            )
        else:
            req = requests.get(
                url, headers=headers, auth=HTTPBasicAuth(self.usr, self.pw)
            )
        if req.status_code == requests.codes.ok:
            return req.content
        else:
            req.raise_for_status()

    def _put_request(self, url, data):
        headers = {"Content-Type": "application/xml"}
        req = requests.put(
            url, headers=headers, auth=HTTPBasicAuth(self.usr, self.pw), data=data
        )
        if req.status_code == requests.codes.ok:
            return req.content
        else:
            req.raise_for_status()

    @property
    def base_url(self):
        return f"http://{self.host}:{self.port}/{self.prefix}/"

    @property
    def root_collection(self):
        return self._root_collection

    @root_collection.setter
    def root_collection(self, collection):
        """
        Set the path to the main collection (e. g. '/db/foo/bar/')
        """

        self._root_collection = collection

    @property
    def root_collection_url(self):
        """
        Get the root collection URL
        """

        data_path = self._join_paths("/rest/", self.root_collection)
        url = urljoin(self.base_url, data_path)
        return url

    def _parse_item(self, node) -> tuple:
        return (node["absid"], node["nodeid"], node[0])

    def query(self, query_expression: str, parser=PARSER) -> delb.Document:
        """
        Make a database query using XQuery
        """
        response_string = self._get_request(
            self.root_collection_url, query=query_expression
        )
        response_node = delb.Document(response_string, parser)
        return response_node

    def retrieve_resources(self, xpath) -> list:
        try:
            results_node = self.query(
                query_expression=f"""for $node in {xpath} return 
                <pyexist-result nodeid="{{util:node-id($node)}}" 
                absid="{{util:absolute-resource-id($node)}}">
                {{$node}}</pyexist-result>"""
            )
        except HTTPError:
            raise ExistAPIError(
                f"""The attempt to retrieve resources with the expression {xpath} 
                failed. The XPath expression might not be valid."""
            )

        results = results_node.css_select("pyexist-result")

        return [
            Resource(exist_client=self, query_result=self._parse_item(item)) for item in results
        ]

    def update_resource(
        self, updated_node: str, abs_resource_id: str, node_id=None
    ) -> None:
        if node_id:
            response = self.query(
                query_expression=f"""
                let $node := 
                util:node-by-id(
                    util:get-resource-by-absolute-id({abs_resource_id}), '{node_id}')
                return update replace $node with {updated_node}
                """
            )
        else:
            response = self.query(
                query_expression=f"""
                let $node := util:get-resource-by-absolute-id({abs_resource_id})
                return update replace $node with {updated_node}
                """
            )

    def retrieve_resource(self, abs_resource_id: str, node_id=None) -> delb.Document:
        if node_id:
            result_node = self.query(
                query_expression=f"""
                util:node-by-id(
                    util:get-resource-by-absolute-id({abs_resource_id}), '{node_id}')"""
            )
        else:
            result_node = self.query(
                query_expression=f"util:get-resource-by-absolute-id({abs_resource_id})"
            )
        return result_node[0]

    def delete_resource(self, abs_resource_id: str, node_id=None) -> None:
        if node_id:
            response = self.query(
                query_expression=f"""
                let $node := util:node-by-id(
                    util:get-resource-by-absolute-id({abs_resource_id}), '{node_id}')
                return update delete $node"""
            )
        else:
            response = self.query(
                query_expression=f"""
                let $node := util:get-resource-by-absolute-id({abs_resource_id})
                return update delete $node"""
            )
