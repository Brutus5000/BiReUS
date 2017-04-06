# coding=utf-8
import abc
import logging
from pathlib import Path
from urllib.request import urlretrieve

from typing import Any

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    def __init__(self, cause: Any, url: str):
        super(DownloadError, self).__init__('Download from %s failed, caused by %s' % (url, repr(cause)))
        self.url = url


class AbstractDownloadService(abc.ABC):
    """
    Offers functionality to download or read files from a remote url.
    Inherit from this class if you want to have more control of the process.
    """

    @abc.abstractmethod
    def download(self, url: str, path: Path) -> None:
        """
        Downloads the file at the given url to given path.
        Needs to throw DownloadError if anything bad happens
        :param url: url to the file
        :param path: destination of the file
        """
        pass

    @abc.abstractmethod
    def read(self, url: str) -> bytes:
        """
        Reads a file from a remote url
        Needs to throw DownloadError if anything bad happens
        :param url: url to the file
        :return: bytes of file from url
        """
        pass


class BasicDownloadService(AbstractDownloadService):
    """
    A simple blocking download service
    """

    def download(self, url: str, path: Path) -> None:
        try:
            logger.debug("Starting download from %s to %s", url, str(path))
            urlretrieve(url, str(path))
        except Exception as e:
            raise DownloadError(e, url)

    def read(self, url: str) -> bytes:
        try:
            logger.debug("Starting download from %s to memory", url)
            filename, httpmessage = urlretrieve(url)
            return Path(filename).read_bytes()
        except Exception as e:
            raise DownloadError(e, url)
