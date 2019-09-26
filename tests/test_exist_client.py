import pytest
import requests
from requests.exceptions import HTTPError
from snakesist.exist_client import ExistClient

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
    # requests.get(f"{BASE_URL}&_query=xmldb:remove('{ROOT_COLL}')")


def test_exist_client_create_resource_wellformed(db):
    new_node = '<example id="t1">wow a document node</example>'
    db.create_resource("/foo", new_node)
    response = requests.get(f"{BASE_URL}&_query=//example[@id='t1']")
    node = response.content.decode()
    assert node == new_node


def test_exist_client_create_resource_malformed(db):
    new_node = '<exapl id="t1">tags do not match</example>'
    with pytest.raises(HTTPError):
        db.create_resource("/foo", new_node)


def test_exist_update_document(db):
    new_node = '<example id="t2">wow a document node</example>'
    updated_node = '<example id="t2">wow a NEW document node</example>'
    db.create_resource("/foo", new_node)
    xq = "let $node := //example[@id='t2'] return util:collection-name($node) || '/' || util:document-name($node)"
    path = requests.get(f"{BASE_URL}&_query={xq}").content.decode()
    db.update_document(updated_node, path)
    response = requests.get(f"{BASE_URL}&_query=//example[@id='t2']")
    node = response.content.decode()
    assert node == updated_node


def test_exist_update_node(db):
    new_node = '<example id="t3"><example id="t4">i am a child</example></example>'
    updated_node = '<example id="t4">i am a child indeed</example>'
    db.create_resource("/foo", new_node)
    xq = "let $node := //example[@id='t4'] return util:absolute-resource-id($node)"
    abs_res_id = requests.get(f"{BASE_URL}&_query={xq}").content.decode()
    xq = "let $node := //example[@id='t4'] return util:node-id($node)"
    node_id = requests.get(f"{BASE_URL}&_query={xq}").content.decode()
    db.update_node(updated_node, abs_res_id, node_id)
    response = requests.get(f"{BASE_URL}&_query=//example[@id='t4']")
    node = response.content.decode()
    assert node == updated_node

