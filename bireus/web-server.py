import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from aiohttp import web, ClientSession

from bireus.server.repository_manager import RepositoryManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WebServer():
    def __init__(self):
        parser = argparse.ArgumentParser(
            description="BiReUS (Bidirectional Repository Update Service) - updater webservice")

        parser.add_argument("--debug", "-d", default='info', choices=['debug', 'info', 'warning', 'error'])
        parser.add_argument("--path", "-p", default=os.getcwd(), help="repository root path")
        parser.add_argument("--port", default=8080, help="repository root path")

        args = parser.parse_args()

        streamhandler = logging.StreamHandler(sys.stdout)
        streamhandler.setLevel(self.get_loglevel(args.debug))
        formatter = logging.Formatter('%(name)-25s - %(levelname)-5s - %(message)s')
        streamhandler.setFormatter(formatter)
        logger.addHandler(streamhandler)

        self.repository_manager = RepositoryManager(Path(args.path))
        self.queue = asyncio.Queue()

        self.app = web.Application()
        self.app.router.add_post('/update', self.handle)

        asyncio.ensure_future(self.process_queue())
        web.run_app(self.app, port=args.port)

    def get_loglevel(self, level: str) -> int:
        if level == 'debug':
            return logging.DEBUG
        elif level == 'info':
            return logging.INFO
        elif level == 'warning':
            return logging.WARNING
        elif level == 'error':
            return logging.ERROR
        else:  # default
            return logging.INFO

    async def process_queue(self):
        while True:
            try:
                logging.debug("Awaiting queue item")
                repository, callback_url, payload = await self.queue.get()

                logging.debug("Updating repository " + repository.name)
                repository.update()

                logging.debug("Performing callback")
                async with ClientSession() as session:
                    async with session.post(callback_url, data=json.dumps(payload)) as response:
                        logger.debug("Status code '%s', body:\n%s", response.status, await response.text())
            except Exception as e:
                logger.exception(e)

    async def handle(self, request):
        data = await request.content.read(int(request.headers['content-length']))
        body = json.loads(data.decode("utf-8"))

        try:
            repo_name = body["repository"]
            callback_url = body["callback_url"]
            payload = body["payload"]
        except KeyError:
            logger.debug("Invalid request: " + repr(request))
            return web.HTTPBadRequest(reason="Invalid arguments",
                                      text="repository, callback_url and payload are required")

        success = False

        for repo in [x for x in self.repository_manager.repositories if x.name == repo_name]:
            logger.debug(
                "Adding to queue: repo='%s', callback_url='%s', payload= '%s'" % (repo.name, callback_url, payload))
            await self.queue.put((repo, callback_url, payload))
            success = True

        if success:
            return web.HTTPAccepted()
        else:
            return web.HTTPNotFound(reason="Invalid arguments",
                                    text="repository, callback_url and payload are required")


if __name__ == '__main__':
    WebServer()
