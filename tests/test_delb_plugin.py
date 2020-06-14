import pytest

from delb import Document, FailedDocumentLoading
from snakesist import ExistClient


@pytest.mark.usefixtures("db")
def test_delete_document():
    url = "existdb://admin:@localhost:8080/exist/test_collection/test_document.xml"
    document = Document(url)
    document.existdb_delete()
    with pytest.raises(FailedDocumentLoading):
        Document(url)


@pytest.mark.usefixtures("db")
def test_load_document_from_url():
    url = "existdb://admin:@localhost:8080/exist/test_collection/test_document.xml"
    document = Document(url)

    assert document.source_url == url
    assert isinstance(document.config.existdb.abs_id, str)
    assert isinstance(document.config.existdb.client, ExistClient)
    assert document.existdb_collection == "/test_collection/"
    assert document.existdb_filename == "test_document.xml"


@pytest.mark.usefixtures("db")
def test_load_document_with_client():
    exist_client = ExistClient(host="localhost", port=8080, user="admin", password="")
    document = Document(
        "/test_collection/test_document.xml", existdb_client=exist_client
    )

    assert (
        document.source_url
        == "existdb://admin:@localhost:8080/exist/test_collection/test_document.xml"
    )
    assert isinstance(document.config.existdb.abs_id, str)
    assert document.config.existdb.client is exist_client
    assert document.existdb_collection == "/test_collection/"
    assert document.existdb_filename == "test_document.xml"


@pytest.mark.usefixtures("db")
def test_store_document():
    document = Document(
        "<test/>",
        existdb_client=ExistClient(
            host="localhost", port=8080, user="admin", password=""
        ),
    )
    document.existdb_store(collection="/test_collection/", filename="new_document.xml")

    document = Document(
        "existdb://admin:@localhost:8080/exist/test_collection/test_document.xml"
    )
    document.existdb_store(replace_existing=True)
    document.existdb_store(
        collection="/another/collection/", filename="another_name.xml",
    )
    assert document.existdb_collection == "/test_collection/"
    assert document.existdb_filename == "test_document.xml"

    document.existdb_collection = "/another/collection/"
    document.existdb_filename = "another_name.xml"
    document.existdb_store(replace_existing=True)
