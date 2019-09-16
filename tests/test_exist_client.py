import pytest
import urllib
import requests
from requests.exceptions import HTTPError
from snakesist.exist_client import Resource, ExistClient

ROOT_COLL = "/db/mock"
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
    new_node = '<example id="t1">wow a document node</example>'
    db.create_resource("/foo", new_node)
    response = requests.get(f"{BASE_URL}&_query=//example[@id='t1']")
    node = response.content
    assert node.decode() == new_node


def test_exist_client_create_resource_malformed(db):
    new_node = '<exapl id="t1">tags do not match</example>'
    with pytest.raises(HTTPError):
        db.create_resource("/projects/test", new_node)
