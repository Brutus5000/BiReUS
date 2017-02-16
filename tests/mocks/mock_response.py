from pathlib import Path

class MockResponse:
    def __init__(self, resp_data, code=200, msg='OK'):
        self.resp_data = resp_data
        self.code = code
        self.msg = msg
        self.headers = {'content-type': 'text/plain; charset=utf-8'}

    def read(self):
        return self.resp_data

    def getcode(self):
        return self.code

    def __enter__(self):
        pass
    def __exit__(self,type, value, tb):
        pass

    @classmethod
    def from_file(cls, path: Path) -> 'MockResponse':
        with open(str(path), 'r') as file:
            content = file.read().encode('utf-8')
            return MockResponse(content)