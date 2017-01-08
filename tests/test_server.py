import filecmp
import json
import os
import shutil
import zipfile

import bsdiff4
import pytest

from server.repository_manager import RepositoryManager, InvalidRepositoryPathError
from shared.DiffHead import DiffHead


def create_simplefile(path: str, name: str, content: str) -> str:
    abs_path = os.path.join(path, name)

    with open(abs_path, 'w+') as file:
        file.write(content)
        return abs_path


@pytest.fixture()
def empty_repo_with_2_version(tmpdir):
    os.chdir(tmpdir.strpath)

    repo_folder = tmpdir.mkdir("test_repo")
    v1_folder = repo_folder.mkdir("v1")
    v2_folder = repo_folder.mkdir("v2")

    versionfile = repo_folder.join(".versions")
    versionfile.write("v1")

    return tmpdir, repo_folder, v1_folder, v2_folder


def test_invalid_repo_folder(tmpdir):
    os.chdir(tmpdir.strpath)

    with pytest.raises(InvalidRepositoryPathError):
        RepositoryManager(os.path.join(tmpdir.strpath, 'non_existing_folder'))


def test_empty_repo(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update()

    with zipfile.ZipFile(os.path.join(v1_folder.strpath, '.delta_to', 'v2.zip')) as baseZip:
        baseZip.extractall(os.path.join(v1_folder.strpath, '.delta_to', 'v2'))

    assert os.path.exists(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus'))  # delta file written
    with open(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus')) as json_file:
        json_result = json.load(json_file)
        assert json_result['repository'] == "test_repo"
        assert json_result['base_version'] == "v1"
        assert json_result['target_version'] == "v2"
        assert len(json_result['items']) == 1
        assert json_result['items'][0]['name'] == ''
        assert json_result['items'][0]['type'] == 'directory'
        assert json_result['items'][0]['action'] == 'delta'
        assert len(json_result['items'][0]['items']) == 0

    delta = DiffHead.load_json_file(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus'))
    assert delta.repository == "test_repo"
    assert delta.base_version == "v1"
    assert delta.target_version == "v2"
    assert len(delta.items) == 1


def test_folder_removed(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v1_folder_FR = v1_folder.mkdir("fr")  # folder FR removed

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update()

    with zipfile.ZipFile(os.path.join(v1_folder.strpath, '.delta_to', 'v2.zip')) as baseZip:
        baseZip.extractall(os.path.join(v1_folder.strpath, '.delta_to', 'v2'))

    result = DiffHead.load_json_file(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "directory"
    assert result.items[0].name == "fr"
    assert result.items[0].action == "remove"
    assert len(result.items[0].items) == 0


def test_folder_added(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v2_folder_FA = v2_folder.mkdir("fa")  # folder FA added

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update()

    with zipfile.ZipFile(os.path.join(v1_folder.strpath, '.delta_to', 'v2.zip')) as baseZip:
        baseZip.extractall(os.path.join(v1_folder.strpath, '.delta_to', 'v2'))

    result = DiffHead.load_json_file(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "directory"
    assert result.items[0].name == "fa"
    assert result.items[0].action == "add"
    assert len(result.items[0].items) == 0


def test_folder_unchanged(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v1_folder_FU = v1_folder.mkdir("fu")  # folder FU unchanged
    v2_folder_FU = v2_folder.mkdir("fu")  # folder FU unchanged

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update()

    with zipfile.ZipFile(os.path.join(v1_folder.strpath, '.delta_to', 'v2.zip')) as baseZip:
        baseZip.extractall(os.path.join(v1_folder.strpath, '.delta_to', 'v2'))

    result = DiffHead.load_json_file(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "directory"
    assert result.items[0].name == "fu"
    assert result.items[0].action == "delta"
    assert len(result.items[0].items) == 0


def test_subfolder_added(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v2_folder_top = v2_folder.mkdir("top")  # folder FA added
    v2_folder_sub = v2_folder_top.mkdir("sub")

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update()

    with zipfile.ZipFile(os.path.join(v1_folder.strpath, '.delta_to', 'v2.zip')) as baseZip:
        baseZip.extractall(os.path.join(v1_folder.strpath, '.delta_to', 'v2'))

    result = DiffHead.load_json_file(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "directory"
    assert result.items[0].name == "top"
    assert result.items[0].action == "add"
    assert len(result.items[0].items) == 1
    assert result.items[0].items[0].type == "directory"
    assert result.items[0].items[0].name == "sub"
    assert result.items[0].items[0].action == "add"


def test_file_removed(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    create_simplefile(v1_folder.strpath, "test.txt", "test")

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update()

    with zipfile.ZipFile(os.path.join(v1_folder.strpath, '.delta_to', 'v2.zip')) as baseZip:
        baseZip.extractall(os.path.join(v1_folder.strpath, '.delta_to', 'v2'))

    result = DiffHead.load_json_file(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "file"
    assert result.items[0].name == "test.txt"
    assert result.items[0].action == "remove"
    assert len(result.items[0].items) == 0


def test_file_added(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    create_simplefile(v2_folder.strpath, "test.txt", "test")

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update()

    with zipfile.ZipFile(os.path.join(v1_folder.strpath, '.delta_to', 'v2.zip')) as baseZip:
        baseZip.extractall(os.path.join(v1_folder.strpath, '.delta_to', 'v2'))

    result = DiffHead.load_json_file(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "file"
    assert result.items[0].name == "test.txt"
    assert result.items[0].action == "add"
    assert len(result.items[0].items) == 0


def test_file_changed(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    create_simplefile(v1_folder.strpath, "test.txt", "Das ist die alte Version!")
    create_simplefile(v2_folder.strpath, "test.txt", "Das ist die neue Version!")

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update()

    with zipfile.ZipFile(os.path.join(v1_folder.strpath, '.delta_to', 'v2.zip')) as baseZip:
        baseZip.extractall(os.path.join(v1_folder.strpath, '.delta_to', 'v2'))

    result = DiffHead.load_json_file(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "file"
    assert result.items[0].name == "test.txt"
    assert result.items[0].action == "bsdiff"
    assert len(result.items[0].items) == 0

    assert os.path.exists(os.path.join(v1_folder.strpath, '.delta_to', 'v2', 'test.txt'))
    bsdiff4.file_patch(os.path.join(v1_folder.strpath, 'test.txt'),
                       os.path.join(v1_folder.strpath, '.delta_to', 'v2', 'test.txt.patched'),
                       os.path.join(v1_folder.strpath, '.delta_to', 'v2', 'test.txt'))
    assert filecmp.cmp(os.path.join(v2_folder.strpath, 'test.txt'),
                       os.path.join(v1_folder.strpath, '.delta_to', 'v2', 'test.txt.patched'))


def test_file_unchanged(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    create_simplefile(v1_folder.strpath, "test.txt", "Das ist die gleiche Version!")
    create_simplefile(v2_folder.strpath, "test.txt", "Das ist die gleiche Version!")

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update()

    with zipfile.ZipFile(os.path.join(v1_folder.strpath, '.delta_to', 'v2.zip')) as baseZip:
        baseZip.extractall(os.path.join(v1_folder.strpath, '.delta_to', 'v2'))

    result = DiffHead.load_json_file(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "file"
    assert result.items[0].name == "test.txt"
    assert result.items[0].action == "unchanged"
    assert len(result.items[0].items) == 0


def test_zipdelta(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v1_zipdir = tmpdir.mkdir("test_zipdelta_v1")
    create_simplefile(v1_zipdir.strpath, "test.txt", "Das ist die alte Version!")
    shutil.make_archive(os.path.join(v1_folder.strpath, "test"), 'zip', v1_zipdir.strpath)

    v2_zipdir = tmpdir.mkdir("test_zipdelta_v2")
    create_simplefile(v2_zipdir.strpath, "test.txt", "Das ist die neue Version!")
    shutil.make_archive(os.path.join(v2_folder.strpath, "test"), 'zip', v2_zipdir.strpath)

    shutil.rmtree(v1_zipdir.strpath)
    shutil.rmtree(v2_zipdir.strpath)

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update()

    with zipfile.ZipFile(os.path.join(v1_folder.strpath, '.delta_to', 'v2.zip')) as baseZip:
        baseZip.extractall(os.path.join(v1_folder.strpath, '.delta_to', 'v2'))

    result = DiffHead.load_json_file(os.path.join(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "file"
    assert result.items[0].name == "test.zip"
    assert result.items[0].action == "zipdelta"
    assert len(result.items[0].items) == 1


def test_cleanup(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version
    delta_folder1 = v1_folder.mkdir(".delta_to").strpath

    assert os.path.exists(delta_folder1)

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_cleanup()

    assert not os.path.exists(delta_folder1)


def test_forward_only(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v2_folder_FA = v2_folder.mkdir("fa")  # folder FA added

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update(forward_only=True)

    assert os.path.exists(os.path.join(v1_folder.strpath, ".delta_to"))
    assert not os.path.exists(os.path.join(v2_folder.strpath, ".delta_to"))


def test_forward_only_negative(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v2_folder_FA = v2_folder.mkdir("fa")  # folder FA added

    repo_manager = RepositoryManager(tmpdir.strpath)
    repo_manager.full_update(forward_only=False)

    assert os.path.exists(os.path.join(v1_folder.strpath, ".delta_to"))
    assert os.path.exists(os.path.join(v2_folder.strpath, ".delta_to"))
