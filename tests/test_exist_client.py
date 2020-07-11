import pytest  # type: ignore
import requests
from _delb.exceptions import FailedDocumentLoading

from delb import Document

from snakesist import ExistClient


def test_exist_client_delete_node(rest_base_url, test_client):
    Document(
        '<example id="t4">i stay<deletee> and i am to be deleted</deletee></example>',
        existdb_client=test_client
    ).existdb_store(filename="foo.xml")

    xq = "let $node := //deletee return util:absolute-resource-id($node)"
    abs_res_id = requests.get(f"{rest_base_url}&_query={xq}").content.decode()
    xq = "let $node := //deletee return util:node-id($node)"
    node_id = requests.get(f"{rest_base_url}&_query={xq}").content.decode()
    test_client.delete_node(abs_res_id, node_id)
    response = requests.get(f"{rest_base_url}&_query=//example[@id='t4']")
    node = response.content.decode()
    assert node == '<example id="t4">i stay</example>'


def test_exist_client_delete_document(rest_base_url, test_client):
    Document(
        '<example id="t5">i am to be deleted</example>', existdb_client=test_client
    ).existdb_store(collection="/bar", filename="foo.xml")
    test_client.delete_document("/bar/foo.xml")
    with pytest.raises(FailedDocumentLoading):
        Document("/bar/foo.xml", existdb_client=test_client)


def test_exist_client_retrieve_resources(test_client):
    paragraph_1 = "<p>retrieve me first!</p>"
    paragraph_2 = "<p>retrieve me too!</p>"
    Document(
        f'<example id="t7">{paragraph_1}</example>', existdb_client=test_client
    ).existdb_store(filename="document_1.xml")
    Document(paragraph_2, existdb_client=test_client).existdb_store(
        filename="document_2.xml"
    )

    retrieved_nodes = test_client.retrieve_resources("//p")
    retrieved_nodes_str = [str(node) for node in retrieved_nodes]
    assert paragraph_1 in retrieved_nodes_str
    assert paragraph_2 in retrieved_nodes_str


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize(
    "url, properties",
    (
        ("existdb://localhost/exist", ("https", "", "", "localhost", 443, "exist")),
        (
            "existdb+https://localhost/exist",
            ("https", "", "", "localhost", 443, "exist"),
        ),
        ("existdb+http://localhost/exist", ("http", "", "", "localhost", 80, "exist")),
        (
            "existdb+http://localhost:8080/exist",
            ("http", "", "", "localhost", 8080, "exist"),
        ),
        (
            "existdb://admin:@localhost/exist",
            ("https", "admin", "", "localhost", 443, "exist"),
        ),
    ),
)
def test_url_parsing(url, properties):
    client = ExistClient.from_url(url)
    assert client.transport == properties[0]
    assert client.user == properties[1]
    assert client.password == properties[2]
    assert client.host == properties[3]
    assert client.port == properties[4]
    assert client.prefix == properties[5]
