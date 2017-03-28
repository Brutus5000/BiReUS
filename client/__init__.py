# coding=utf-8
from typing import Dict

from client.patch_task import AbstractPatchTask, PatchTaskV1

patch_tasks = dict()  # type: Dict

patch_tasks[PatchTaskV1.get_version()] = PatchTaskV1.create
