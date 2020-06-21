import pytest  # type: ignore
import requests
from requests.exceptions import ConnectionError


def is_responsive(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True
    except ConnectionError:
        return False


@pytest.fixture(scope="session")
def db_url(docker_services, docker_ip):
    port = docker_services.port_for("existdb", 8080)
    url = f"http://{docker_ip}:{port}"
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_responsive(url)
    )
    return url


def test_db_instance_exists(db_url):
    response = requests.get(f"{db_url}/exist")
    assert response.status_code == 200


@pytest.mark.parametrize("doc_path", ["hugo_ball/manifest.xml"])
def test_documents_exist(db_url, doc_path):
    response = requests.get(f"{db_url}/exist/rest/db/apps/test-data/{doc_path}")
    assert response.status_code == 200
