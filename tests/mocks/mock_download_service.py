from pathlib import Path

from client.download_service import AbstractDownloadService


class MockDownloadService(AbstractDownloadService):
    def __init__(self, download_function=[]):
        if isinstance(download_function, list):
            self._download_function = download_function
        else:
            self._download_function = [download_function]

    def add_download_action(self, download_function) -> None:
        self._download_function.append(download_function)

    async def download(self, url: str, path: Path) -> None:
        self._download_function.pop(0)(url, path)

