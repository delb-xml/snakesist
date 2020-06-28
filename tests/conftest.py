from pathlib import Path

import requests
from pytest import fixture  # type: ignore

from snakesist import ExistClient


@fixture
def rest_base_url(test_client):
    test_client.root_collection = "/db/tests"
    return (
        f"{test_client.base_url}rest{test_client.root_collection}?_wrap=no&_indent=no"
    )


def existdb_is_responsive(url):
    try:
        response = requests.head(url)
        assert response.status_code == 200
    except Exception:
        return False
    else:
        return True


@fixture
def db(docker_ip, docker_services):
    """
    Database setup and teardown
    """
    base_url = f"http://{docker_ip}:{docker_services.port_for('existdb', 8080)}"
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: existdb_is_responsive(base_url)
    )
    return base_url


@fixture(scope="session")
def docker_compose_file(pytestconfig):
    return str(Path(__file__).parent.resolve() / "db_fixture" / "docker-compose.yml")


@fixture
def test_client(db):
    host, port = db[len("http://") :].split(":")
    client = ExistClient(
        host=host, port=int(port), prefix="exist/", user="admin", password="",
    )
    yield client
