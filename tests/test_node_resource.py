import pytest


@pytest.mark.usefixtures("sample_document")
def test_delete(test_client):
    items = test_client.xpath("//item")
    assert len(items) == 2
    items[-1].delete()
    items = test_client.xpath("//item")
    assert len(items) == 1


@pytest.mark.usefixtures("sample_document")
def test_document_path(test_client):
    resource = test_client.xpath("/root/list")[0]
    assert resource.document_path == "/db/tests/sample.xml"


def test_update_push_and_pull(sample_document, test_client):
    resource = test_client.xpath("//list")[0]
    resource.node.local_name = "lost"
    resource.update_push()

    document = test_client.fetch_document("sample.xml")
    assert document.xpath("//lost").size == 1

    resource.node.local_name = "ooops"
    resource.update_pull()
    assert resource.node.local_name == "lost"
