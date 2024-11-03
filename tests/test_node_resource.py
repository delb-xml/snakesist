import pytest


@pytest.mark.usefixtures("sample_document")
def test_delete(test_client):
    items = test_client.xpath("//item")
    assert len(items) == 2
    items[-1].delete()
    items = test_client.xpath("//item")
    assert len(items) == 1
