import os
import delb
import requests
from lxml import etree
from lxml.etree import XMLSyntaxError
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from urllib.parse import urljoin, quote, unquote


NSD_TEI = "{http://www.tei-c.org/ns/1.0}"
NSD_XML = "{http://www.w3.org/XML/1998/namespace}"
NSD_EXIST = "{http://exist.sourceforge.net/NS/exist}"


class ExistAPIError(Exception):
    """
    Raised when the eXist-db API throws an error
    """

    pass


class ExistDocument:
    """
    A wrapper for an eXist-db XML document.
    This wrapper contains the actual document object as a property.
    """

    def __init__(self, engine, relative_doc_path, node, error=None):
        self._node = node
        self.error = error
        self.engine = engine
        self.path = relative_doc_path

    def __str__(self):
        return os.path.basename(self.url)

    @property
    def node(self):
        """
        Get the XML document node
        """
        return self._node

    @node.setter
    def node(self, node):
        """
        Set the XML document node
        """
        input_type = delb.Document
        if isinstance(node, input_type):
            self._node = node
        else:
            raise TypeError(f"Provided node must be {input_type}.")

    @property
    def url(self):
        """
        Get the full URL pointing to the document in the database
        """
        url_parts = (self.engine.root_collection_url, self.path)
        return "/".join(s.strip("/") for s in url_parts)

    def save(self):
        """Save document via the configured database engine."""
        self.engine.save(self)


class ExistInstance:
    def __init__(self, url="http://localhost:8080/exist/", usr="admin", pw=""):
        """
        Initialize a database instance for retreiving, manipulating, 
        and saving XML documents.
        
        :param url: The basic root URL pointing to an eXist-db instance
        :param usr: eXist-db username
        :param pw: eXist-db password
        """

        self.base_url = url
        self.documents = []
        self._root_collection = "/"
        self.usr = usr
        self.pw = pw

    @staticmethod
    def _join_paths(*args):
        return "/".join(s.strip("/") for s in args)

    def _get_request(self, url):
        headers = {"Content-Type": "application/xml"}
        req = requests.get(url, headers=headers, auth=HTTPBasicAuth(self.usr, self.pw))
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

    def save(self, document):
        """
        Save a document to the configured database
        """

        url = document.url
        data = str(document.node).encode("utf-8")
        self._put_request(url, data)

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

    def load_document(self, relative_collection_path):
        """
        Load an XML document from a path relative to the configured 
        root collection
        """

        url = self._join_paths(self.root_collection_url, relative_collection_path)
        parser = etree.XMLParser()
        try:
            response_body = self._get_request(url)
            node = delb.Document(response_body, parser)
            document = ExistDocument(self, relative_collection_path, node)
        except HTTPError as e:
            # Ignore HTTP errors if file format is not XML
            if not url.lower().endswith(".xml"):
                return
            elif "%" in url:
                raise ExistAPIError(
                    f'Cannot load "{os.path.basename(url)}". The special characters in the '
                    "document name might be preventing eXist-db from returning a valid response."
                )
                return
            else:
                raise e
        except (XMLSyntaxError, ValueError) as e:
            # Try to recover not well-formed documents and save error
            lazy_parser = etree.XMLParser(recover=True)
            response_body = self._get_request(url)
            lxml_etree = etree.fromstring(response_body, lazy_parser)
            node = delb.Document(lxml_etree)
            document = ExistDocument(self, relative_collection_path, node, error=e)
        self.documents.append(document)

    def load_all_documents(self, collection=""):
        """
        Load all XML documents recursively from the configured 
        root collection downwards
        """

        path = collection
        url = self._join_paths(self.root_collection_url, path)
        response_body = self._get_request(url)
        root = etree.fromstring(response_body)
        collections = root.iterfind(f"{NSD_EXIST}collection//{NSD_EXIST}collection")
        resources = root.iterfind(f"{NSD_EXIST}collection//{NSD_EXIST}resource")
        for r in resources:
            resource_name = r.attrib["name"]
            collection_path = self._join_paths(path, resource_name)
            self.load_document(collection_path)
        for c in collections:
            collection_name = c.attrib["name"]
            collection_path = self._join_paths(path, collection_name)
            self.load_all_documents(collection=collection_path)

    def get_document(self, document_path) -> ExistDocument:
        """
        Retrieve an already loaded document using a path relative to 
        the configured root collection
        """

        url = self._join_paths(self.root_collection_url, document_path)
        for document in self.documents:
            if document.url == url:
                return document
        raise ValueError(
            "Document not found. Check if document is loaded or if the path is correct."
        )
