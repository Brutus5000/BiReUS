import logging
import abc
import atexit
from pathlib import Path
from typing import Union

import aiohttp

logger = logging.getLogger(__name__)


class AbstractDownloadService(abc.ABC):
    @abc.abstractmethod
    async def download(self, url: str, path: Path) -> None:
        pass


class BasicDownloadService(AbstractDownloadService):
    def __init__(self):
        self._session = aiohttp.ClientSession()
        atexit.register(self._session.close)

    async def download(self, url: str, path: Path) -> None:
        chunk_size = 1024

        async with self._session.get(url) as resp:
            with path.open(mode="wb") as file:
                while True:
                    chunk = await resp.content.read(chunk_size)
                    if not chunk:
                        break
                    file.write(chunk)
