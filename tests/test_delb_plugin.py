import pytest

from delb import Document, FailedDocumentLoading
from snakesist import ExistClient
from snakesist.exceptions import SnakesistConfigError, SnakesistWriteError


def test_delete_document(test_client):
    filename = "delete_document.xml"
    document = Document("<delete/>", existdb_client=test_client)
    document.existdb_store(filename=filename)
    document.existdb_delete()
    with pytest.raises(FailedDocumentLoading):
        Document(f"existdb://admin:@localhost:8080/exist/db/tests/{filename}")


def test_filename(sample_document):
    assert sample_document.existdb_filename == "sample.xml"


def test_invalid_client(test_client):
    with pytest.raises(SnakesistConfigError):
        Document("<foo/>", existdb_client=0)

    document = Document("<foo/>", existdb_client=test_client)
    document.config.existdb.client = 0
    with pytest.raises(SnakesistConfigError):
        document.existdb_store(filename="foo.xml")


@pytest.mark.usefixtures("db")
def test_load_document_from_url():
    url = "existdb://admin:@localhost:8080/exist/db/apps/test-data/dada_manifest.xml"
    document = Document(url)

    assert document.source_url == url
    assert isinstance(document.config.existdb.client, ExistClient)
    assert document.existdb_collection == "/db/apps/test-data"
    assert document.existdb_filename == "dada_manifest.xml"


def test_load_document_with_client(test_client):
    test_client.root_collection = "/db/apps/"
    document = Document("/test-data/dada_manifest.xml", existdb_client=test_client)

    assert document.config.existdb.client is test_client
    assert document.existdb_collection == "/test-data"
    assert document.existdb_filename == "dada_manifest.xml"


def test_store_document(test_client):
    test_client.root_collection = "/db/apps/"
    document = Document(
        "<test/>",
        existdb_client=test_client,
    )
    document.existdb_store(collection="/test_collection/", filename="new_document.xml")

    document = Document(
        "existdb://admin:@localhost:8080/exist/db/apps/test-data/dada_manifest.xml"
    )
    document.existdb_store(replace_existing=True)
    assert document.existdb_collection == "/db/apps/test-data"
    assert document.existdb_filename == "dada_manifest.xml"

    document.existdb_store(
        collection="/another/collection/",
        filename="another_name.xml",
    )
    document.existdb_collection = "/another/collection/"
    document.existdb_filename = "another_name.xml"
    with pytest.raises(SnakesistWriteError):
        document.existdb_store()

    test_client.root_collection = "/"
    document.existdb_collection = collection = "/db/apps/test_collection/"
    document.existdb_filename = filename = "new_document.xml"
    document.existdb_store(replace_existing=True)
    assert (
        Document(f"{collection}{filename}", existdb_client=test_client).root.local_name
        != "test"
    )


@pytest.mark.usefixtures("db")
def test_with_other_extension():
    document = Document("existdb://localhost/exist/db/apps/test-data/dada_manifest.xml")
    assert document.tei_header.title == "Das erste dadaistische Manifest"
    assert document.tei_header.authors == ["Ball, Hugo"]
