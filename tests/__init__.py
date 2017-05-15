import tempfile
from pathlib import Path

from bireus.shared import compare_files, unpack_archive


def assert_file_equals(file_or_folder_A: Path, file_or_folder_B: Path, file_name=None) -> None:
    if file_name is None:
        assert compare_files(file_or_folder_A, file_or_folder_B)
    else:
        assert compare_files(file_or_folder_A.joinpath(file_name), file_or_folder_B.joinpath(file_name))


def assert_zip_file_equals(file_or_folder_A: Path, file_or_folder_B: Path, file_name=None) -> None:
    if file_name is None:
        file_a = file_or_folder_A
        file_b = file_or_folder_B
    else:
        file_a = file_or_folder_A.joinpath(file_name)
        file_b = file_or_folder_B.joinpath(file_name)

    temp_dir_obj = tempfile.TemporaryDirectory(prefix="bireus_unittest_")

    temp_dir_path = Path(temp_dir_obj.name)
    try:
        temp_a = temp_dir_path.joinpath("a")
        temp_a.mkdir()
        temp_b = temp_dir_path.joinpath("b")
        temp_b.mkdir()

        unpack_archive(file_a, temp_a, "zip")
        unpack_archive(file_b, temp_b, "zip")

        file_list_a = list(temp_a.glob("**/*"))
        file_list_b = list(temp_b.glob("**/*"))

        relative_list = []

        for file in file_list_a:
            if file.is_file():
                relative_list.append(file.relative_to(temp_a))

        for file in file_list_b:
            if file.is_dir():
                continue

            relative_path = file.relative_to(temp_b)

            assert relative_path in relative_list
            assert_file_equals(temp_a.joinpath(relative_path), temp_b.joinpath(relative_path))
            relative_list.remove(relative_path)

        assert len(relative_list) == 0


    finally:
        temp_dir_obj.cleanup()
