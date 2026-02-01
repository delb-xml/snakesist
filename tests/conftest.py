from os import getenv
from pathlib import Path

import httpx
from delb import Document
from pytest import fixture

from snakesist import ExistClient


SAMPLE_DOCUMENT = """\
<root>
  <list>
    <item>one</item>
    <item>two</item>
  </list>
</root>
"""


exist_version_is_verified = False


@fixture
def rest_base_url(test_client):
    return f"{test_client.root_collection_url}?_wrap=no&_indent=no"


def existdb_is_responsive(url):
    try:
        httpx.head(url).raise_for_status()
    except Exception:
        return False
    else:
        return True


@fixture(autouse=True)
def certificate(monkeypatch):
    monkeypatch.setenv(
        "SSL_CERT_FILE",
        str(Path(__file__).resolve().parent / "db_fixture" / "nginx" / "cert.pem"),
    )


@fixture(scope="session")
def db(docker_ip, docker_services):
    """
    Database setup and teardown
    """
    base_url = f"http://{docker_ip}:{docker_services.port_for('existdb', 8080)}"
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: existdb_is_responsive(base_url)
    )
    yield base_url


@fixture(scope="session")
def docker_compose_file():
    return str(Path(__file__).parent.resolve() / "db_fixture" / "docker-compose.yml")


@fixture
def sample_document(test_client):
    document = Document(SAMPLE_DOCUMENT, existdb_client=test_client)
    document.existdb_store(filename="sample.xml", replace_existing=True)
    yield document


@fixture
def test_client(db):
    host, port = db.removeprefix("http://").split(":")
    client = ExistClient(
        host=host,
        port=int(port),
        prefix="exist/",
        user="admin",
        password="",
        root_collection="/db/tests",
    )

    global exist_version_is_verified
    if not exist_version_is_verified:
        assert (
            getenv("EXIST_VERSION") == client.query("system:get-version()")[0].full_text
        )
        exist_version_is_verified = True

    yield client
