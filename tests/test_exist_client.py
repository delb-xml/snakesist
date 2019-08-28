import pytest
import requests
import requests_mock
from snakesist.exist_client import Resource, ExistClient

@pytest.fixture
@requests_mock.Mocker()
def initalize_db_mocker(m):
    query = {
        'retrieve': f"""util:node-by-id(
            util:get-resource-by-absolute-id(2568390447132), '1.6.2.3.17.8.2')"""
    }
    m.get(
        f"""http://localhost:8080/exist/rest/db/mock?_howmany=0
            &_query={query['retrieve']}""",
        text="""<exist:result exist:hits="1" exist:start="1" exist:count="1" 
            exist:compilation-time="0" exist:execution-time="0">
            <corr cert="high">liberazione</corr></exist:result>"""
    )

def test_exist_client_retrieve():
    db = ExistClient()
    resource = db.retrieve_resource("2568390447132", "1.6.2.3.17.8.2")
    assert str(resource) == '<corr xmlns="http://www.tei-c.org/ns/1.0" cert="high">liberazione</corr>'
