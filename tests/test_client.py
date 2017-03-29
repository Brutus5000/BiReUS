# coding=utf-8
import json
import logging
import sys

import networkx
import pytest

from client.download_service import DownloadError
from client.repository import ClientRepository, CheckoutError
from server.repository_manager import RepositoryManager
from shared import *
from shared.repository import ProtocolException
from tests.create_test_server_data import create_test_server_data
from tests.mocks.mock_download_service import MockDownloadService

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)-25s - %(levelname)-5s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

server_path = Path.cwd().joinpath("example-server")
client_path = Path.cwd().joinpath("example-client")
test_url = "http://localhost:12345/subfolder/subsub"


@pytest.fixture()
def prepare_server():
    # create demo repo
    create_test_server_data(server_path, "inst-bi")
    RepositoryManager(server_path).full_update()
    if client_path.exists():
        remove_folder(client_path)

    yield prepare_server

    # teardown


async def get_latest_version(mocker, downloader) -> ClientRepository:
    global client_repo

    downloader.add_read_action(lambda url: server_path.joinpath("repo_demo", "info.json").read_bytes())
    version_graph = server_path.joinpath("repo_demo", "versions.gml")
    server_latest = server_path.joinpath("repo_demo", "latest.tar.xz")
    downloader.add_download_action(lambda path_from, path_to: copy_file(version_graph, path_to))
    downloader.add_download_action(lambda path_from, path_to: copy_file(server_latest, path_to))

    return await ClientRepository.get_from_url(client_path, test_url, downloader)


@pytest.mark.asyncio
async def test_get_from_url_folder_exists():
    Path("example-client").mkdir(exist_ok=True)
    with pytest.raises(FileExistsError):
        await ClientRepository.get_from_url(client_path, test_url, MockDownloadService(lambda: None))


@pytest.mark.asyncio
async def test_get_from_url_http_error():
    remove_folder(client_path)
    with pytest.raises(DownloadError):
        await ClientRepository.get_from_url(client_path, test_url,
                                            MockDownloadService(lambda: None, lambda url: (_ for _ in ()).throw(
                                                DownloadError(None, url))))


@pytest.mark.asyncio
async def test_get_from_url_success(mocker, prepare_server):
    downloader = MockDownloadService()
    await get_latest_version(mocker, downloader)

    assert len(downloader.urls_called) == 3
    assert downloader.urls_called[0] == test_url + "/info.json"
    assert downloader.urls_called[1] == test_url + "/versions.gml"
    assert downloader.urls_called[2] == test_url + "/latest.tar.xz"

    assert client_path.joinpath(".bireus", "info.json").exists()
    assert compare_files(client_path.joinpath("changed.txt"), server_path.joinpath("repo_demo", "v2", "changed.txt"))
    assert compare_files(client_path.joinpath("changed.zip"), server_path.joinpath("repo_demo", "v2", "changed.zip"))
    assert compare_files(client_path.joinpath("unchanged.txt"),
                         server_path.joinpath("repo_demo", "v2", "unchanged.txt"))
    assert compare_files(client_path.joinpath("new_folder", "new_file.txt"),
                         server_path.joinpath("repo_demo", "v2", "new_folder", "new_file.txt"))


@pytest.mark.asyncio
async def test_checkout_version_success(mocker, prepare_server):
    downloader = MockDownloadService()
    client_repo = await get_latest_version(mocker, downloader)

    server_update = server_path.joinpath("repo_demo", "__patches__", "v2_to_v1.tar.xz")
    downloader.add_download_action(lambda path_from, path_to: copy_file(server_update, path_to))

    await client_repo.checkout_version("v1")

    assert len(downloader.urls_called) == 4
    # repo initialization
    assert downloader.urls_called[0] == test_url + "/info.json"
    assert downloader.urls_called[1] == test_url + "/versions.gml"
    assert downloader.urls_called[2] == test_url + "/latest.tar.xz"

    # checkout version -> download patch
    assert downloader.urls_called[3] == test_url + "/__patches__/v2_to_v1.tar.xz"

    assert compare_files(client_path.joinpath("changed.txt"), server_path.joinpath("repo_demo", "v1", "changed.txt"))
    assert client_path.joinpath("changed.zip").exists()  # zips are not binary identical
    assert compare_files(client_path.joinpath("removed.txt"), server_path.joinpath("repo_demo", "v1", "removed.txt"))
    assert compare_files(client_path.joinpath("unchanged.txt"),
                         server_path.joinpath("repo_demo", "v1", "unchanged.txt"))
    assert compare_files(client_path.joinpath("removed_folder", "obsolete.txt"),
                         server_path.joinpath("repo_demo", "v1", "removed_folder", "obsolete.txt"))


@pytest.mark.asyncio
async def test_checkout_version_unknown(mocker, prepare_server):
    downloader = MockDownloadService()
    client_repo = await get_latest_version(mocker, downloader)
    downloader.add_read_action(lambda url: server_path.joinpath("repo_demo", "info.json").read_bytes())

    with pytest.raises(CheckoutError):
        await client_repo.checkout_version("unknown_version")

    assert len(downloader.urls_called) == 4
    # repo initialization
    assert downloader.urls_called[0] == test_url + "/info.json"
    assert downloader.urls_called[1] == test_url + "/versions.gml"
    assert downloader.urls_called[2] == test_url + "/latest.tar.xz"

    # unknown version -> check whether we know the latest version
    assert downloader.urls_called[3] == test_url + "/info.json"


@pytest.mark.asyncio
async def test_checkout_version_twice_success(mocker, prepare_server):
    downloader = MockDownloadService()
    client_repo = await get_latest_version(mocker, downloader)

    server_patch_2_to_1_zip = str(server_path.joinpath("repo_demo", "__patches__", "v2_to_v1.tar.xz"))
    downloader.add_download_action(lambda path_from, path_to: copy_file(server_patch_2_to_1_zip, path_to))
    await client_repo.checkout_version("v1")

    server_patch_1_to_2_zip = str(server_path.joinpath("repo_demo", "__patches__", "v1_to_v2.tar.xz"))
    downloader.add_download_action(lambda path_from, path_to: copy_file(server_patch_1_to_2_zip, path_to))
    downloader.add_read_action(lambda url: server_path.joinpath("repo_demo", "info.json").read_bytes())
    await client_repo.checkout_version("v2")

    assert len(downloader.urls_called) == 5
    # repo initialization
    assert downloader.urls_called[0] == test_url + "/info.json"
    assert downloader.urls_called[1] == test_url + "/versions.gml"
    assert downloader.urls_called[2] == test_url + "/latest.tar.xz"

    # checkout version -> download patch
    assert downloader.urls_called[3] == test_url + "/__patches__/v2_to_v1.tar.xz"
    assert downloader.urls_called[4] == test_url + "/__patches__/v1_to_v2.tar.xz"

    assert client_path.joinpath(".bireus", "info.json").exists()
    assert compare_files(client_path.joinpath("changed.txt"), server_path.joinpath("repo_demo", "v2", "changed.txt"))
    assert client_path.joinpath("changed.zip").exists()  # zips are not binary identical
    assert compare_files(client_path.joinpath("unchanged.txt"),
                         server_path.joinpath("repo_demo", "v2", "unchanged.txt"))
    assert compare_files(client_path.joinpath("new_folder", "new_file.txt"),
                         server_path.joinpath("repo_demo", "v2", "new_folder", "new_file.txt"))


@pytest.mark.asyncio
async def test_checkout_version_crc_mismatch_before_patching(mocker, prepare_server):
    downloader = MockDownloadService()
    client_repo = await get_latest_version(mocker, downloader)

    with client_path.joinpath("changed.txt").open("wb") as file:
        file.write("test".encode("utf-8"))

    server_update = server_path.joinpath("repo_demo", "__patches__", "v2_to_v1.tar.xz")
    downloader.add_download_action(lambda path_from, path_to: copy_file(server_update, path_to))

    server_single_file = server_path.joinpath("repo_demo", "v1", "changed.txt")
    downloader.add_download_action(lambda path_from, path_to: copy_file(server_single_file, path_to))

    await client_repo.checkout_version("v1")

    assert len(downloader.urls_called) == 5
    # repo initialization
    assert downloader.urls_called[0] == test_url + "/info.json"
    assert downloader.urls_called[1] == test_url + "/versions.gml"
    assert downloader.urls_called[2] == test_url + "/latest.tar.xz"

    # checkout version -> download patch
    assert downloader.urls_called[3] == test_url + "/__patches__/v2_to_v1.tar.xz"

    # version mismatch -> download file from original repo instead
    assert downloader.urls_called[4] == test_url + "/v1/changed.txt"

    assert compare_files(client_path.joinpath("changed.txt"), server_path.joinpath("repo_demo", "v1", "changed.txt"))
    assert client_path.joinpath("changed.zip").exists()  # zips are not binary identical
    assert compare_files(client_path.joinpath("removed.txt"), server_path.joinpath("repo_demo", "v1", "removed.txt"))
    assert compare_files(client_path.joinpath("unchanged.txt"),
                         server_path.joinpath("repo_demo", "v1", "unchanged.txt"))
    assert compare_files(client_path.joinpath("removed_folder", "obsolete.txt"),
                         server_path.joinpath("repo_demo", "v1", "removed_folder", "obsolete.txt"))


def test_protocol_exception(tmpdir):
    repo_folder = tmpdir.mkdir("repo_demo")
    bireus_folder = repo_folder.mkdir(".bireus")

    info_json = bireus_folder.join("info.json")
    with info_json.open("w") as file:
        json.dump(
            {
                "name": "repo_demo",
                "first_version": "v1",
                "latest_version": "v1",
                "current_version": "v1",
                "strategy": "inst-bi",
                "protocol": 999
            },
            file
        )

    version_graph = networkx.DiGraph()
    version_graph.add_node("v1")
    networkx.write_gml(version_graph, str(bireus_folder.join("versions.gml")))

    with pytest.raises(ProtocolException):
        ClientRepository(Path(repo_folder.strpath))
