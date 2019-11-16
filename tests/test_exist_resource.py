import pytest
import requests

from snakesist import ExistClient

ROOT_COLL = "/db/tests"
BASE_URL = f"http://admin:@localhost:8080/exist/rest{ROOT_COLL}?_wrap=no&_indent=no"


@pytest.fixture
def db():
    """
    Database setup and teardown
    """
    db = ExistClient()
    db.root_collection = ROOT_COLL
    yield db
    requests.get(f"{BASE_URL}&_query=xmldb:remove('{ROOT_COLL}')")


def test_exist_document_update_push(db):
    new_node = '<example id="ta">wow a document node</example>'
    db.create_resource("/foo", new_node)
    updated_node = '<example id="ta">wow a document node???</example>'
    doc = db.retrieve_resources("//example[@id='ta']").pop()
    doc.root.append_child("???")
    doc.update_push()
    response = requests.get(f"{BASE_URL}&_query=//example[@id='ta']")
    node = response.content.decode()
    assert node == updated_node


def test_exist_document_update_pull(db):
    new_node = '<example id="tc">wow a document node</example>'
    db.create_resource("/foo", new_node)
    doc_1 = db.retrieve_resources("//example[@id='tc']").pop()
    doc_2 = db.retrieve_resources("//example[@id='tc']").pop()
    doc_1.root.append_child("???")
    doc_1.update_push()
    doc_2.update_pull()
    assert str(doc_1.root) == str(doc_2.root)


def test_exist_document_delete(db):
    new_node = '<example id="tb">wow a document node</example>'
    db.create_resource("/foo", new_node)
    doc = db.retrieve_resources("//example[@id='tb']").pop()
    doc.delete()
    response = requests.get(f"{BASE_URL}&_query=//example[@id='tb']")
    node = response.content.decode()
    assert node == ""
