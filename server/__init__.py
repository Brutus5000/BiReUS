import os
from typing import List


def get_subdirectories(path: str) -> List[str]:
    return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)) and d != '.delta_to' and d != '__patches__']


def get_files(path: str) -> List[str]:
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
