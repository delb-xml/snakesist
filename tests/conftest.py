from os import getenv
from pathlib import Path

import httpx
import pytest
from delb import Document

from delb_existdb import ExistClient

SAMPLE_DOCUMENT = """\
<root>
  <list>
    <item>one</item>
    <item>two</item>
  </list>
</root>
"""


exist_version_is_verified = False


@pytest.fixture
def rest_base_url(test_client):
    return f"{test_client.root_collection_url}?_wrap=no&_indent=no"


def existdb_is_responsive(url):
    try:
        httpx.head(url).raise_for_status()
    except Exception:
        return False
    else:
        return True


@pytest.fixture(autouse=True)
def _certificate(monkeypatch):
    monkeypatch.setenv(
        "SSL_CERT_FILE",
        str(Path(__file__).resolve().parent / "db_fixture" / "nginx" / "cert.pem"),
    )


@pytest.fixture(scope="session")
def db(docker_ip, docker_services):
    """
    Database setup and teardown
    """
    base_url = f"http://{docker_ip}:{docker_services.port_for('existdb', 8080)}"
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: existdb_is_responsive(base_url)
    )
    return base_url


@pytest.fixture(scope="session")
def docker_compose_file():
    return str(Path(__file__).parent.resolve() / "db_fixture" / "docker-compose.yml")


@pytest.fixture
def sample_document(test_client):
    document = Document(SAMPLE_DOCUMENT, existdb_client=test_client)
    document.existdb_store(filename="sample.xml", replace_existing=True)
    return document


@pytest.fixture
def test_client(db):
    host, port = db.removeprefix("http://").split(":")
    client = ExistClient(
        host=host,
        port=int(port),
        prefix="exist/",
        user="admin",
        password="",
        root_collection="/db/apps/test-data",
    )

    global exist_version_is_verified
    if not exist_version_is_verified:
        assert (
            getenv("EXIST_VERSION") == client.query("system:get-version()")[0].full_text
        )
        exist_version_is_verified = True

    return client
