# coding=utf-8
import abc
import atexit
import logging
from pathlib import Path
from typing import Any

import aiohttp

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
    async def download(self, url: str, path: Path) -> None:
        """
        Downloads the file at the given url to given path.
        Needs to throw DownloadError if anything bad happens
        :param url: url to the file
        :param path: destination of the file
        """
        pass

    @abc.abstractmethod
    async def read(self, url: str) -> bytes:
        """
        Reads a file from a remote url
        Needs to throw DownloadError if anything bad happens
        :param url: url to the file
        :return: bytes of file from url
        """
        pass


class BasicDownloadService(AbstractDownloadService):
    """
    A simple async download service
    """

    def __init__(self):
        self._session = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
            atexit.register(self._session.close)
        return self._session

    async def download(self, url: str, path: Path) -> None:
        chunk_size = 1024

        try:
            session = await self.get_session()
            logger.debug("Starting download from %s to %s", url, str(path))
            async with session.get(url) as response:
                with path.open(mode="wb") as file:
                    if response.status != 200:
                        raise Exception("404 - File not found")

                    while True:
                        chunk = await response.content.read(chunk_size)
                        if not chunk:
                            break
                        file.write(chunk)
        except Exception as e:
            raise DownloadError(e, url)

    async def read(self, url: str) -> bytes:
        try:
            session = await self.get_session()
            logger.debug("Starting download from %s to memory", url)
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception("404 - File not found")

                return await response.read()
        except Exception as e:
            raise DownloadError(e, url)
