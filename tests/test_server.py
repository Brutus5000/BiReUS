# coding=utf-8
import json

import bsdiff4
import networkx
import pytest

from server.repository_manager import RepositoryManager, InvalidRepositoryPathError
from shared import *
from shared.diff_head import DiffHead


def create_simplefile(path: str, name: str, content: str) -> str:
    abs_path = Path(path, name)
    abs_path.write_text(content)
    return str(abs_path)


@pytest.fixture()
def empty_repo_with_2_version(tmpdir):
    repo_folder = tmpdir.mkdir("repo_demo")
    v1_folder = repo_folder.mkdir("v1")
    v2_folder = repo_folder.mkdir("v2")

    info_json = repo_folder.join("info.json")
    with info_json.open("w") as file:
        json.dump(
            {
                "config": {
                    "name": "repo_demo",
                    "first_version": "v1",
                    "latest_version": "v1",
                    "strategy": "inst-bi"
                },
            },
            file
        )

    version_graph = networkx.DiGraph()
    version_graph.add_node("v1")
    networkx.write_gml(version_graph, str(repo_folder.join("versions.gml")))

    return tmpdir, repo_folder, v1_folder, v2_folder


def test_load_empty_repo(tmpdir):
    main_path = Path(tmpdir.strpath)
    repo_path = main_path.joinpath("repo_demo")
    repo_path.mkdir()
    version_graph = networkx.DiGraph()
    version_graph.add_node("v1")
    networkx.write_gml(version_graph, str(repo_path.joinpath("versions.gml")))

    repo_path.joinpath("v1").mkdir()
    info_json = repo_path.joinpath("info.json")

    with info_json.open("w") as file:
        json.dump(
            {
                "config": {
                    "name": "repo_demo",
                    "first_version": "v1",
                    "latest_version": "v1",
                    "strategy": "inst-bi"
                },
            },
            file
        )

    repo_manager = RepositoryManager(main_path)
    assert repo_manager.repositories[0].name == "repo_demo"
    assert repo_manager.repositories[0].first_version == "v1"
    assert repo_manager.repositories[0].latest_version == "v1"
    assert len(list(repo_manager.repositories[0].version_graph)) == 1
    assert list(repo_manager.repositories[0].version_graph)[0] == "v1"


def test_invalid_repo_folder(tmpdir):
    os.chdir(tmpdir.strpath)

    with pytest.raises(InvalidRepositoryPathError):
        RepositoryManager(Path(tmpdir.strpath, 'non_existing_folder'))


def test_empty_repo(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    filename = Path(repo_folder.strpath, '__patches__', 'v1_to_v2.tar.xz')
    targetfolder = Path(v1_folder.strpath, '.delta_to', 'v2')
    unpack_archive(filename, targetfolder, 'xztar')

    assert Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus').exists()  # delta file written
    with Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus').open() as json_file:
        json_result = json.load(json_file)
        assert json_result['repository'] == "repo_demo"
        assert json_result['base_version'] == "v1"
        assert json_result['target_version'] == "v2"
        assert len(json_result['items']) == 1
        assert json_result['items'][0]['name'] == ''
        assert json_result['items'][0]['type'] == 'directory'
        assert json_result['items'][0]['action'] == 'delta'
        assert len(json_result['items'][0]['items']) == 0

    delta = DiffHead.load_json_file(Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus'))
    assert delta.repository == "repo_demo"
    assert delta.base_version == "v1"
    assert delta.target_version == "v2"
    assert len(delta.items) == 1


def test_folder_removed(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v1_folder_FR = v1_folder.mkdir("fr")  # folder FR removed

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    filename = Path(repo_folder.strpath, '__patches__', 'v1_to_v2.tar.xz')
    targetfolder = Path(v1_folder.strpath, '.delta_to', 'v2')
    unpack_archive(filename, targetfolder, 'xztar')

    result = DiffHead.load_json_file(Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "directory"
    assert result.items[0].name == "fr"
    assert result.items[0].action == "remove"
    assert len(result.items[0].items) == 0


def test_folder_added(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v2_folder_FA = v2_folder.mkdir("fa")  # folder FA added

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    filename = Path(repo_folder.strpath, '__patches__', 'v1_to_v2.tar.xz')
    targetfolder = Path(v1_folder.strpath, '.delta_to', 'v2')
    unpack_archive(filename, targetfolder, 'xztar')

    result = DiffHead.load_json_file(Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "directory"
    assert result.items[0].name == "fa"
    assert result.items[0].action == "add"
    assert len(result.items[0].items) == 0


def test_folder_unchanged(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v1_folder_FU = v1_folder.mkdir("fu")  # folder FU unchanged
    v2_folder_FU = v2_folder.mkdir("fu")  # folder FU unchanged

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    filename = Path(repo_folder.strpath, '__patches__', 'v1_to_v2.tar.xz')
    targetfolder = Path(v1_folder.strpath, '.delta_to', 'v2')
    unpack_archive(filename, targetfolder, 'xztar')

    result = DiffHead.load_json_file(Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "directory"
    assert result.items[0].name == "fu"
    assert result.items[0].action == "delta"
    assert len(result.items[0].items) == 0


def test_subfolder_added(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v2_folder_top = v2_folder.mkdir("top")  # folder FA added
    v2_folder_sub = v2_folder_top.mkdir("sub")

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    filename = Path(repo_folder.strpath, '__patches__', 'v1_to_v2.tar.xz')
    targetfolder = Path(v1_folder.strpath, '.delta_to', 'v2')
    unpack_archive(filename, targetfolder, 'xztar')

    result = DiffHead.load_json_file(Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
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

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    filename = Path(repo_folder.strpath, '__patches__', 'v1_to_v2.tar.xz')
    targetfolder = Path(v1_folder.strpath, '.delta_to', 'v2')
    unpack_archive(filename, targetfolder, 'xztar')

    result = DiffHead.load_json_file(Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "file"
    assert result.items[0].name == "test.txt"
    assert result.items[0].action == "remove"
    assert len(result.items[0].items) == 0


def test_file_added(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    create_simplefile(v2_folder.strpath, "test.txt", "test")

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    filename = Path(repo_folder.strpath, '__patches__', 'v1_to_v2.tar.xz')
    targetfolder = Path(v1_folder.strpath, '.delta_to', 'v2')
    unpack_archive(filename, targetfolder, 'xztar')

    result = DiffHead.load_json_file(Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "file"
    assert result.items[0].name == "test.txt"
    assert result.items[0].action == "add"
    assert len(result.items[0].items) == 0


def test_file_changed(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    create_simplefile(v1_folder.strpath, "test.txt", "Das ist die alte Version!")
    create_simplefile(v2_folder.strpath, "test.txt", "Das ist die neue Version!")

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    filename = Path(repo_folder.strpath, '__patches__', 'v1_to_v2.tar.xz')
    targetfolder = Path(v1_folder.strpath, '.delta_to', 'v2')
    unpack_archive(filename, targetfolder, 'xztar')

    result = DiffHead.load_json_file(Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "file"
    assert result.items[0].name == "test.txt"
    assert result.items[0].action == "bsdiff"
    assert len(result.items[0].items) == 0

    assert Path(v1_folder.strpath, '.delta_to', 'v2', 'test.txt').exists()
    bsdiff4.file_patch(str(Path(v1_folder.strpath, 'test.txt')),
                       str(Path(v1_folder.strpath, '.delta_to', 'v2', 'test.txt.patched')),
                       str(Path(v1_folder.strpath, '.delta_to', 'v2', 'test.txt')))
    assert compare_files(Path(v2_folder.strpath, 'test.txt'),
                         Path(v1_folder.strpath, '.delta_to', 'v2', 'test.txt.patched'))


def test_file_unchanged(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    create_simplefile(v1_folder.strpath, "test.txt", "Das ist die gleiche Version!")
    create_simplefile(v2_folder.strpath, "test.txt", "Das ist die gleiche Version!")

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    filename = Path(repo_folder.strpath, '__patches__', 'v1_to_v2.tar.xz')
    targetfolder = Path(v1_folder.strpath, '.delta_to', 'v2')
    unpack_archive(filename, targetfolder, 'xztar')

    result = DiffHead.load_json_file(Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "file"
    assert result.items[0].name == "test.txt"
    assert result.items[0].action == "unchanged"
    assert len(result.items[0].items) == 0


def test_zipdelta(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v1_zipdir = tmpdir.mkdir("test_zipdelta_v1")
    create_simplefile(v1_zipdir.strpath, "test.txt", "Das ist die alte Version!")
    make_archive(Path(v1_folder.strpath, "test"), 'zip', v1_zipdir.strpath)

    v2_zipdir = tmpdir.mkdir("test_zipdelta_v2")
    create_simplefile(v2_zipdir.strpath, "test.txt", "Das ist die neue Version!")
    make_archive(Path(v2_folder.strpath, "test"), 'zip', v2_zipdir.strpath)

    remove_folder(v1_zipdir.strpath)
    remove_folder(v2_zipdir.strpath)

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    filename = Path(repo_folder.strpath, '__patches__', 'v1_to_v2.tar.xz')
    targetfolder = Path(v1_folder.strpath, '.delta_to', 'v2')
    unpack_archive(filename, targetfolder, 'xztar')

    result = DiffHead.load_json_file(Path(v1_folder.strpath, '.delta_to', 'v2', '.bireus')).items[0]
    assert len(result.items) == 1
    assert result.items[0].type == "file"
    assert result.items[0].name == "test.zip"
    assert result.items[0].action == "zipdelta"
    assert len(result.items[0].items) == 1


def test_cleanup(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    Path(repo_folder.strpath, "__patches__").mkdir()

    Path(repo_folder.strpath, "__patches__", "v1_to_v2.tar.xz").touch()
    Path(repo_folder.strpath, "__patches__", "v2_to_v1.tar.xz").touch()

    assert Path(repo_folder.strpath, "__patches__", "v1_to_v2.tar.xz").exists()
    assert Path(repo_folder.strpath, "__patches__", "v2_to_v1.tar.xz").exists()

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_cleanup()

    assert not Path(repo_folder.strpath, "__patches__", "v1_to_v2.tar.xz").exists()
    assert not Path(repo_folder.strpath, "__patches__", "v2_to_v1.tar.xz").exists()


def test_forward_only(tmpdir):
    repo_folder = tmpdir.mkdir("repo_demo")
    v1_folder = repo_folder.mkdir("v1")
    v2_folder = repo_folder.mkdir("v2")

    info_json = repo_folder.join("info.json")
    with info_json.open("w") as file:
        json.dump(
            {
                "config": {
                    "name": "repo_demo",
                    "first_version": "v1",
                    "latest_version": "v1",
                    "strategy": "inst-fo"
                },
            },
            file
        )

    version_graph = networkx.DiGraph()
    version_graph.add_node("v1")
    networkx.write_gml(version_graph, str(repo_folder.join("versions.gml")))

    v2_folder_FA = v2_folder.mkdir("fa")  # folder FA added

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    assert Path(repo_folder.strpath, "__patches__", "v1_to_v2.tar.xz").exists()
    assert not Path(repo_folder.strpath, "__patches__", "v2_to_v1.tar.xz").exists()


def test_forward_only_negative(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v2_folder_FA = v2_folder.mkdir("fa")  # folder FA added

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    assert Path(repo_folder.strpath, "__patches__", "v1_to_v2.tar.xz").exists()
    assert Path(repo_folder.strpath, "__patches__", "v2_to_v1.tar.xz").exists()


def test_create_repository(tmpdir):
    path = Path(tmpdir.strpath)
    repo_manager = RepositoryManager(path)
    repo_manager.create("new_repo")

    with path.joinpath("new_repo", "info.json").open("r") as file:
        info_json = json.load(file)

    assert path.joinpath("new_repo", "1.0.0").exists()
    assert info_json["config"]["name"] == "new_repo"
    assert info_json["config"]["latest_version"] == "1.0.0"
    assert info_json["config"]["strategy"] == "inst-bi"

    version_graph_path = path.joinpath("new_repo", "versions.gml")
    version_graph = networkx.read_gml(str(version_graph_path))
    assert len(list(version_graph)) == 1


def test_create_repository_2(tmpdir):
    path = Path(tmpdir.strpath)
    repo_manager = RepositoryManager(path)
    repo_manager.create("new_repo", "v1", "inc-fo")

    with path.joinpath("new_repo", "info.json").open("r") as file:
        info_json = json.load(file)

    assert path.joinpath("new_repo", "v1").exists()
    assert info_json["config"]["name"] == "new_repo"
    assert info_json["config"]["latest_version"] == "v1"
    assert info_json["config"]["strategy"] == "inc-fo"

    version_graph_path = path.joinpath("new_repo", "versions.gml")
    version_graph = networkx.read_gml(str(version_graph_path))
    assert len(list(version_graph)) == 1


def test_update_3_repos(empty_repo_with_2_version):
    tmpdir, repo_folder, v1_folder, v2_folder = empty_repo_with_2_version

    v3_folder = repo_folder.mkdir("v3")

    repo_manager = RepositoryManager(Path(tmpdir.strpath))
    repo_manager.full_update()

    with Path(repo_folder.strpath, "info.json").open("r") as file:
        info_json = json.load(file)

    assert info_json['config']['latest_version'] == "v3"

    assert Path(repo_folder.strpath, "__patches__", "v1_to_v3.tar.xz").exists()
    assert Path(repo_folder.strpath, "__patches__", "v1_to_v2.tar.xz").exists()
    assert Path(repo_folder.strpath, "__patches__", "v2_to_v1.tar.xz").exists()
    assert Path(repo_folder.strpath, "__patches__", "v3_to_v1.tar.xz").exists()
