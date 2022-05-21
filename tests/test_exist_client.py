import pytest  # type: ignore
import requests

from delb import Document, FailedDocumentLoading

from snakesist import ExistClient


def test_exist_client_delete_node(rest_base_url, test_client):
    Document(
        '<example id="t4">i stay<deletee> and i am to be deleted</deletee></example>',
        existdb_client=test_client,
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


def test_exist_client_xpath(test_client):
    paragraph_1 = "<p>retrieve me first!</p>"
    paragraph_2 = "<p>retrieve me too!</p>"
    Document(
        f'<example id="t7">{paragraph_1}</example>', existdb_client=test_client
    ).existdb_store(filename="document_1.xml")
    Document(paragraph_2, existdb_client=test_client).existdb_store(
        filename="document_2.xml"
    )

    retrieved_nodes = test_client.xpath("//p")
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


def test_query_with_lengthy_contents(test_client):
    long_paragraph = (
        "<p>All fully developed machinery consists of three essentially different"
        " parts, the motor mechanism, the transmitting mechanism, and finally the"
        " tool or working machine. The motor mechanism is that which puts the who"
        "le in motion. It either generates its own motive power, like the steam-e"
        "ngine, the caloric engine, the electromagnetic machine, &c., or it recei"
        "ves its impulse from some already existing natural force, like the water"
        "-wheel from a head of water, the wind-mill from wind, &c. The transmitti"
        "ng mechanism, composed of fly-wheels, shafting, toothed wheels, pullies,"
        " straps, ropes, bands, pinions, and gearing of the most varied kinds, re"
        "gulates the motion, changes its form where necessary, as for instance, f"
        "rom linear to circular, and divides and distributes it among the working"
        " machines. These two first parts of the whole mechanism are there, solel"
        "y for putting the working machines in motion, by means of which motion t"
        "he subject of labour is seized upon and modified as desired. The tool or"
        " working machine is that part of the machinery with which the industrial"
        " revolution of the 18th century started. And to this day it constantly s"
        "erves as such a starting-point, whenever a handicraft, or a manufacture,"
        " is turned into an industry carried on by machinery.</p>"
    )
    Document(
        f'<example id="t8">{long_paragraph}</example>', existdb_client=test_client
    ).existdb_store(filename="document_3.xml")

    retrieved_nodes = test_client.xpath("//p")
    retrieved_nodes_str = [str(node) for node in retrieved_nodes]
    assert long_paragraph in retrieved_nodes_str
