from os import getenv
from pathlib import Path

import httpx
from pytest import fixture

from snakesist import ExistClient


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


@fixture
def db(docker_ip, docker_services, monkeypatch):
    """
    Database setup and teardown
    """
    monkeypatch.setenv(
        "SSL_CERT_FILE",
        str(Path(__file__).resolve().parent / "db_fixture" / "nginx" / "cert.pem"),
    )
    base_url = f"http://{docker_ip}:{docker_services.port_for('existdb', 8080)}"
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: existdb_is_responsive(base_url)
    )
    yield base_url


@fixture(scope="session")
def docker_compose_file():
    return str(Path(__file__).parent.resolve() / "db_fixture" / "docker-compose.yml")


@fixture
def test_client(db):
    host, port = db[len("http://") :].split(":")
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
        assert getenv("EXIST_VERSION") == client.query("system:get-version()")[0].text
        exist_version_is_verified = True

    yield client
