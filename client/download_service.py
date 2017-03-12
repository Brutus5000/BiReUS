import logging
import abc
import atexit
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    def __init__(self, cause: Exception, url: str):
        super(DownloadError, self).__init__('Download from %s failed, caused by %s' % (url, repr(cause)))
        self.url = url


class AbstractDownloadService(abc.ABC):
    @abc.abstractmethod
    async def download(self, url: str, path: Path) -> None:
        pass

    @abc.abstractmethod
    async def read(self, url: str) -> bytes:
        pass


class BasicDownloadService(AbstractDownloadService):
    def __init__(self):
        self._session = None

    async def get_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
            atexit.register(self._session.close)
        return self._session

    async def download(self, url: str, path: Path) -> None:
        chunk_size = 1024

        try:
            session = await self.get_session()
            async with session.get(url) as response:
                with path.open(mode="wb") as file:
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
            async with session.get(url) as response:
                return await response.read()
        except Exception as e:
            raise DownloadError(e, url)
