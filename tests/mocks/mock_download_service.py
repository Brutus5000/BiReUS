from pathlib import Path

from client.download_service import AbstractDownloadService


class MockDownloadService(AbstractDownloadService):
    def __init__(self, download_function):
        self._download_function = download_function

    @property
    def download_action(self):
        return self._download_function

    @download_action.setter
    def download_action(self, value):
        self._download_function = value

    async def download(self, url: str, path: Path) -> None:
        self._download_function()
