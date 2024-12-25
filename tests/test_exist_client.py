import pytest
import httpx

from delb import compare_trees, Document, FailedDocumentLoading

from snakesist import ExistClient


def test_delete_document(rest_base_url, test_client):
    Document(
        '<example id="t5">i am to be deleted</example>', existdb_client=test_client
    ).existdb_store(collection="/bar", filename="foo.xml")
    test_client.delete_document("/bar/foo.xml")
    with pytest.raises(FailedDocumentLoading):
        Document("/bar/foo.xml", existdb_client=test_client)


def test_delete_node(rest_base_url, test_client):
    Document(
        '<example id="t4">i stay<deletee> and i am to be deleted</deletee></example>',
        existdb_client=test_client,
    ).existdb_store(filename="foo.xml")

    xq = "let $node := //deletee return util:absolute-resource-id($node)"
    abs_res_id = httpx.get(f"{rest_base_url}&_query={xq}").content.decode()
    xq = "let $node := //deletee return util:node-id($node)"
    node_id = httpx.get(f"{rest_base_url}&_query={xq}").content.decode()
    test_client.delete_node(abs_res_id, node_id)
    response = httpx.get(f"{rest_base_url}&_query=//example[@id='t4']")
    node = response.content.decode()
    assert node == '<example id="t4">i stay</example>'


def test_query_with_lengthy_contents(test_client):
    document = Document("existdb://localhost/exist/db/apps/test-data/dada_manifest.xml")
    long_paragraph = document.root.full_text * 5  # 30625 characters total length
    Document(
        f'<example id="t8"><p>{long_paragraph}</p></example>',
        existdb_client=test_client,
    ).existdb_store(filename="the_long_dada.xml")

    retrieved_nodes = test_client.xpath(f'//p[contains(., "{long_paragraph}")]')
    assert len(retrieved_nodes) == 1


@pytest.mark.usefixtures("sample_document")
def test_fetch_node(test_client):
    xpath_result = test_client.xpath("//list")[0]
    resource = test_client.fetch_node(xpath_result.document_id, xpath_result.node_id)
    assert compare_trees(xpath_result.node, resource.node)


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


def test_xpath(test_client):
    paragraph_1 = "<x>retrieve me first!</x>"
    paragraph_2 = "<x>retrieve me too!</x>"
    Document(
        f'<example id="t7">{paragraph_1}</example>', existdb_client=test_client
    ).existdb_store(filename="document_1.xml")
    Document(paragraph_2, existdb_client=test_client).existdb_store(
        filename="document_2.xml"
    )

    retrieved_nodes = test_client.xpath("//x")
    assert [str(node) for node in retrieved_nodes] == [paragraph_1, paragraph_2]
