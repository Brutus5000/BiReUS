from pathlib import Path

from client.download_service import AbstractDownloadService


class MockDownloadService(AbstractDownloadService):
    def __init__(self, download_function = None, read_function = None):
        if download_function is None:
            self._download_function = []
        elif isinstance(download_function, list):
            self._download_function = download_function
        else:
            self._download_function = [download_function]

        if read_function is None:
            self._read_function = []
        elif isinstance(read_function, list):
            self._read_function = read_function
        else:
            self._read_function = [read_function]

        self.urls_called = []  # type: List[str]

    def add_download_action(self, download_function) -> None:
        self._download_function.append(download_function)

    async def download(self, url: str, path: Path) -> None:
        self.urls_called.append(url)
        self._download_function.pop(0)(url, path)

    def add_read_action(self, read_function) -> None:
        self._read_function.append(read_function)

    async def read(self, url: str) -> bytes:
        self.urls_called.append(url)
        return self._read_function.pop(0)(url)
