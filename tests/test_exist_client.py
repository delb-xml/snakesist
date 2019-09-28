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
    requests.get(f"{BASE_URL}&_query=xmldb:remove('{ROOT_COLL}')")


def test_exist_client_create_resource_wellformed(db):
    new_node = '<example id="t1">wow a <foo>document</foo> node</example>'
    db.create_resource("/foo", new_node)
    response = requests.get(f"{BASE_URL}&_query=//example[@id='t1']")
    node = response.content.decode()
    assert node == new_node


def test_exist_client_create_resource_malformed(db):
    new_node = '<exapl id="t1">tags do not match</example>'
    with pytest.raises(HTTPError):
        db.create_resource("/foo", new_node)


def test_exist_client_update_document(db):
    new_node = '<example id="t2">wow a document node</example>'
    updated_node = '<example id="t2">wow a NEW document node</example>'
    db.create_resource("/foo", new_node)
    xq = "let $node := //example[@id='t2'] return util:collection-name($node) || '/' || util:document-name($node)"
    path = requests.get(f"{BASE_URL}&_query={xq}").content.decode()
    db.update_document(updated_node, path)
    response = requests.get(f"{BASE_URL}&_query=//example[@id='t2']")
    node = response.content.decode()
    assert node == updated_node


def test_exist_client_update_node(db):
    new_node = '<example id="t3">i am a <subnode>child</subnode></example>'
    updated_node = '<subnode>child indeed</subnode>'
    db.create_resource("/foo", new_node)
    xq = "let $node := //subnode return util:absolute-resource-id($node)"
    abs_res_id = requests.get(f"{BASE_URL}&_query={xq}").content.decode()
    xq = "let $node := //subnode return util:node-id($node)"
    node_id = requests.get(f"{BASE_URL}&_query={xq}").content.decode()
    db.update_node(updated_node, abs_res_id, node_id)
    response = requests.get(f"{BASE_URL}&_query=//subnode")
    node = response.content.decode()
    assert node == updated_node


def test_exist_client_delete_node(db):
    new_node = '<example id="t4">i stay<deletee> and i am to be deleted</deletee></example>'
    remaining_node = '<example id="t4">i stay</example>'
    db.create_resource("/foo", new_node)
    xq = "let $node := //deletee return util:absolute-resource-id($node)"
    abs_res_id = requests.get(f"{BASE_URL}&_query={xq}").content.decode()
    xq = "let $node := //deletee return util:node-id($node)"
    node_id = requests.get(f"{BASE_URL}&_query={xq}").content.decode()
    db.delete_node(abs_res_id, node_id)
    response = requests.get(f"{BASE_URL}&_query=//example[@id='t4']")
    node = response.content.decode()
    assert node == remaining_node


def test_exist_client_delete_document(db):
    new_node = '<example id="t5">i am to be deleted</example>'
    db.create_resource("/foo", new_node)
    xq = "let $node := //example[@id='t5'] return util:collection-name($node) || '/' || util:document-name($node)"
    path = requests.get(f"{BASE_URL}&_query={xq}").content.decode()
    db.delete_document(path)
    response = requests.get(f"{BASE_URL}&_query=//example[@id='t5']")
    node = response.content.decode()
    assert node == ""


def test_exist_client_retrieve_resource(db):
    new_node = '<example id="t6">retrieve me!</example>'
    db.create_resource("/foo", new_node)
    xq = "let $node := //example[@id='t6'] return util:absolute-resource-id($node)"
    abs_id = requests.get(f"{BASE_URL}&_query={xq}").content.decode()
    retrieved_node = db.retrieve_resource(abs_resource_id=abs_id)
    assert new_node == str(retrieved_node)


def test_exist_client_retrieve_resources(db):
    node_resource = '<p>retrieve me first!</p>'
    node_resource_doc = f'<example id="t7">{node_resource}</example>'
    db.create_resource("/foo", node_resource_doc)
    document_resource = '<p>retrieve me too!</p>'
    db.create_resource("/foo", document_resource)
    retrieved_nodes = db.retrieve_resources("//p")
    retrieved_nodes_str = [str(node) for node in retrieved_nodes]
    assert node_resource in retrieved_nodes_str
    assert document_resource in retrieved_nodes_str
