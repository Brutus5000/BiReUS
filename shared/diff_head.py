import json
from pathlib import Path
from typing import List, Dict, Any

from shared.diff_item import DiffItem


class DiffHead(object):
    def __init__(self, repository: str, base_version: str, target_version: str, items: List[DiffItem] = []):
        self._repository = repository
        self._base_version = base_version
        self._target_version = target_version
        self._items = []
        self._items.extend(items)

    @property
    def repository(self) -> str:
        return self._repository

    @property
    def base_version(self) -> str:
        return self._base_version

    @property
    def target_version(self) -> str:
        return self._target_version

    @property
    def items(self) -> List[DiffItem]:
        return self._items

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'repository': self.repository,
            'base_version': self.base_version,
            'target_version': self.target_version,
            'items': []
        }

        for item in self.items:
            result['items'].append(item.to_dict())

        return result

    @staticmethod
    def load_dict(data: Dict[str, Any]) -> 'DiffHead':
        result = DiffHead(repository=data['repository'],
                          base_version=data['base_version'],
                          target_version=data['target_version'])

        for sub_dict in data['items']:
            result.items.append(DiffItem.load_dict(sub_dict))

        return result

    @staticmethod
    def load_json_file(filepath: Path) -> 'DiffHead':
        with filepath.open(mode='r') as file:
            return DiffHead.load_dict(json.load(file))
