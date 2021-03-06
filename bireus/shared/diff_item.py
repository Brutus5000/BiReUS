# coding=utf-8
from typing import List, Any, Dict


class DiffItem(object):
    """
    Represents an item of a .bireus file (file or directory)
    """

    def __init__(self, iotype: str, name: str, base_crc, target_crc, action: str = '', items: List['DiffItem'] = None):
        if items is None:
            items = []

        self._type = iotype
        self._name = name
        self._action = action
        self._items = items  # type: List['DiffItem']

        self._base_crc = base_crc
        self._target_crc = target_crc

    @property
    def type(self) -> str:
        return self._type

    @property
    def name(self) -> str:
        return self._name

    @property
    def action(self) -> str:
        return self._action

    @action.setter
    def action(self, value: str) -> None:
        self._action = value

    @property
    def items(self) -> List['DiffItem']:
        return self._items

    @property
    def base_crc(self) -> str:
        return self._base_crc

    @base_crc.setter
    def base_crc(self, value: str) -> None:
        self._base_crc = value

    @property
    def target_crc(self) -> str:
        return self._target_crc

    @target_crc.setter
    def target_crc(self, value: str) -> None:
        self._target_crc = value

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'type': self._type,
            'name': self._name,
            'action': self._action,
            'items': []
        }

        if self._type == "file":
            result['target_crc'] = self._target_crc
            result['base_crc'] = self._base_crc

        for item in self._items:
            result['items'].append(item.to_dict())

        return result

    @staticmethod
    def load_dict(data: Dict[str, Any]) -> 'DiffItem':
        base_crc = ''
        target_crc = ''
        if data['type'] == 'file':
            base_crc = data['base_crc']
            target_crc = data['target_crc']

        result = DiffItem(iotype=data['type'],
                          name=data['name'],
                          base_crc=base_crc,
                          target_crc=target_crc,
                          action=data['action'])

        for sub_dict in data['items']:
            result.items.append(DiffItem.load_dict(sub_dict))

        return result
