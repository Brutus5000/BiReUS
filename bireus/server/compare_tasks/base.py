# coding=utf-8
import abc
import logging

from bireus.shared import *
from bireus.shared.repository import ProtocolException

logger = logging.getLogger(__name__)


class CompareTask(abc.ABC):
    _compare_tasks = None

    def __init__(self, absolute_path: Path, name: str, base: str, target: str, is_zipdelta: bool = False):
        self._absolute_path = absolute_path
        self.name = name
        self.base = base
        self.target = target
        self.is_zipdelta = is_zipdelta

        self._basepath = absolute_path.joinpath(self.base)  # type: Path
        self._targetpath = absolute_path.joinpath(self.target)  # type: Path
        self._deltapath = absolute_path.joinpath(self.base, '.delta_to', self.target)

    @abc.abstractclassmethod
    def get_version(cls) -> int:
        pass

    @abc.abstractclassmethod
    def create(cls, absolute_path: Path, name: str, base: str, target: str,
               is_zipdelta: bool = False) -> 'CompareTask':
        pass

    @classmethod
    def get_factory(cls, protocol: int):
        if cls._compare_tasks is None:
            cls._compare_tasks = dict()
            for compare_task_version in CompareTask.__subclasses__():
                cls._compare_tasks[compare_task_version.get_version()] = compare_task_version.create

        if protocol in cls._compare_tasks:
            return cls._compare_tasks[protocol]
        else:
            raise ProtocolException("Protocol version `%s` is not supported in this server version", protocol)
