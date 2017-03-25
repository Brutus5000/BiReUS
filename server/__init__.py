# coding=utf-8
from pathlib import Path
from typing import List

from server.patch_strategy import IncrementalStrategy, InstantStrategy, MajorMinorStrategy

patching_strategies = dict()
patching_strategies["inc-bi"] = IncrementalStrategy()
patching_strategies["inc-fo"] = IncrementalStrategy(bidirectional=False)
patching_strategies["inst-bi"] = InstantStrategy()
patching_strategies["inst-fo"] = InstantStrategy(bidirectional=False)
patching_strategies["major-bi"] = MajorMinorStrategy()
patching_strategies["major-fo"] = MajorMinorStrategy(bidirectional=False)


def get_subdirectory_names(path: Path) -> List[str]:
    return [d.name for d in path.iterdir() if d.is_dir() and d.name != '.delta_to' and d.name != '__patches__']


def get_filenames(path: Path) -> List[str]:
    return [f.name for f in path.iterdir() if f.is_file()]
