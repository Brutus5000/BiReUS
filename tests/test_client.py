import urllib
import shutil
import filecmp
import logging
import sys
from urllib.request import urlopen
from pathlib import Path

import pytest
from pytest_mock import mocker

from shared import *

from tests.create_test_server_data import create_test_server_data
from tests.mocks.mock_response import MockResponse

from client.repository import Repository, CheckoutError
from server.repository_manager import RepositoryManager

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)-25s - %(levelname)-5s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

server_path = Path.cwd().joinpath("example-server")
client_path = Path.cwd().joinpath("example-client")
client_repo = None


@pytest.fixture()
def prepare_server():
    # create demo repo
    create_test_server_data(server_path)
    RepositoryManager(str(server_path)).full_update()
    if client_path.exists():
        remove_folder(client_path)

    yield prepare_server

    # teardown


@pytest.fixture()
def with_latest_version(mocker, prepare_server):
    global client_repo

    mock_urlopen = mocker.patch("urllib.request.urlopen")
    mock_urlopen.return_value.__enter__.side_effect = [MockResponse.from_file(server_path.joinpath("repo_demo", "info.json")),
                                                       MockResponse.from_file(server_path.joinpath("repo_demo", ".versions"))]

    mock_urlretrieve = mocker.patch("urllib.request.urlretrieve")
    mock_urlretrieve.return_value = [str(server_path.joinpath("repo_demo", "latest.tar.xz")), dict()]

    client_repo = Repository.get_from_url(client_path, "http://localhost:12345")


def test_get_from_url_folder_exists():
    Path("example-client").mkdir(exist_ok=True)
    with pytest.raises(FileExistsError):
        Repository.get_from_url(client_path,"http://localhost:12345")


def test_get_from_url_http_error():
    remove_folder(client_path)
    with pytest.raises(urllib.error.URLError):
        Repository.get_from_url(client_path,"http://localhost:12345")


def test_get_from_url_success(with_latest_version):
    assert client_path.joinpath(".bireus", "info.json").exists()
    assert filecmp.cmp(str(client_path.joinpath("changed.txt")), str(server_path.joinpath("repo_demo", "v2", "changed.txt")))
    assert filecmp.cmp(str(client_path.joinpath("changed.zip")), str(server_path.joinpath("repo_demo", "v2", "changed.zip")))
    assert filecmp.cmp(str(client_path.joinpath("unchanged.txt")), str(server_path.joinpath("repo_demo", "v2", "unchanged.txt")))
    assert filecmp.cmp(str(client_path.joinpath("new_folder", "new_file.txt")), str(server_path.joinpath("repo_demo", "v2", "new_folder", "new_file.txt")))


def test_checkout_version_success(mocker, with_latest_version):
    global client_repo

    server_update_zip = str(server_path.joinpath("repo_demo", "v2", ".delta_to", "v1.tar.xz"))

    mock_urlretrieve = mocker.patch("urllib.request.urlretrieve")
    mock_urlretrieve.return_value = ["", dict()]
    mock_urlretrieve.side_effect = lambda path_from, path_to: copy_file(server_update_zip, path_to)
    client_repo.checkout_version("v1")

    assert filecmp.cmp(str(client_path.joinpath("changed.txt")), str(server_path.joinpath("repo_demo", "v1", "changed.txt")))
    assert client_path.joinpath("changed.zip").exists()  # zips are not binary identical
    assert filecmp.cmp(str(client_path.joinpath("removed.txt")), str(server_path.joinpath("repo_demo", "v1", "removed.txt")))
    assert filecmp.cmp(str(client_path.joinpath("unchanged.txt")), str(server_path.joinpath("repo_demo", "v1", "unchanged.txt")))
    assert filecmp.cmp(str(client_path.joinpath("removed_folder", "obsolete.txt")), str(server_path.joinpath("repo_demo", "v1", "removed_folder", "obsolete.txt")))


def test_checkout_version_unknown(mocker, with_latest_version):
    global client_repo

    server_update_zip = str(server_path.joinpath("repo_demo", "v2", ".delta_to", "v1.tar.xz"))

    mock_urlretrieve = mocker.patch("urllib.request.urlretrieve")
    mock_urlretrieve.return_value = ["", dict()]
    mock_urlretrieve.side_effect = lambda path_from, path_to: copy_file(server_update_zip, path_to)

    with pytest.raises(CheckoutError):
        client_repo.checkout_version("unknown_version")


def test_checkout_version_twice_success(mocker, with_latest_version):
    global client_repo

    server_update_zip = str(server_path.joinpath("repo_demo", "v2", ".delta_to", "v1.tar.xz"))

    mock_urlretrieve = mocker.patch("urllib.request.urlretrieve")
    mock_urlretrieve.return_value = ["", dict()]
    mock_urlretrieve.side_effect = lambda path_from, path_to: copy_file(server_update_zip, path_to)
    client_repo.checkout_version("v1")

    mock_urlopen = mocker.patch("urllib.request.urlopen")
    mock_urlopen.return_value.__enter__.side_effect = [MockResponse.from_file(server_path.joinpath("repo_demo", "info.json")),
                                                       MockResponse.from_file(server_path.joinpath("repo_demo", ".versions"))]

    server_update_zip = str(server_path.joinpath("repo_demo", "v1", ".delta_to", "v2.tar.xz"))

    mock_urlretrieve = mocker.patch("urllib.request.urlretrieve")
    mock_urlretrieve.return_value = ["", dict()]
    mock_urlretrieve.side_effect = lambda path_from, path_to: copy_file(server_update_zip, path_to)
    client_repo.checkout_version("v2")

    assert client_path.joinpath(".bireus", "info.json").exists()
    assert filecmp.cmp(str(client_path.joinpath("changed.txt")), str(server_path.joinpath("repo_demo", "v2", "changed.txt")))
    assert client_path.joinpath("changed.zip").exists()  # zips are not binary identical
    assert filecmp.cmp(str(client_path.joinpath("unchanged.txt")), str(server_path.joinpath("repo_demo", "v2", "unchanged.txt")))
    assert filecmp.cmp(str(client_path.joinpath("new_folder", "new_file.txt")), str(server_path.joinpath("repo_demo", "v2", "new_folder", "new_file.txt")))
