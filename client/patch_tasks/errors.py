# coding=utf-8
from pathlib import Path


class CrcMismatchError(Exception):
    def __init__(self, file: Path, expected_crc: str, actual_crc: str):
        super(CrcMismatchError, self).__init__(self, 'File %s with wrong CRC code (expected=%s, actual=%s)' % (
            str(file), expected_crc, actual_crc))
        self.file = file
        self.expectedCrc = expected_crc
        self.actualCrc = actual_crc
