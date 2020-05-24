import requests
from pytest import fixture

from snakesist import ExistClient


ROOT_COLL = "/db/tests"


@fixture
def base_url():
    return f"http://admin:@localhost:8080/exist/rest{ROOT_COLL}?_wrap=no&_indent=no"


@fixture
def db(base_url):
    """
    Database setup and teardown
    """
    db = ExistClient()
    db.root_collection = ROOT_COLL
    yield db
    requests.get(f"{base_url}&_query=xmldb:remove('{ROOT_COLL}')")
