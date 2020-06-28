import pytest  # type: ignore
import requests


def test_db_instance_exists(db):
    response = requests.get(f"{db}/exist/")
    response.raise_for_status()


@pytest.mark.parametrize("doc_path", ["dada_manifest.xml"])
def test_documents_exist(db, doc_path):
    response = requests.get(f"{db}/exist/rest/db/apps/test-data/{doc_path}")
    assert response.status_code == 200
