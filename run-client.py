#!/usr/bin/env python3
"""Bidirectional Repository Update Service - client component"""
import argparse
import logging
import os
import sys
from pathlib import Path

from client.repository import Repository

root = logging.getLogger()
root.setLevel(logging.DEBUG)


class Client(object):
    def __init__(self):
        parser = argparse.ArgumentParser(
            description="BiReUS (Bidirectional Repository Update Service) - client component",
            usage='''run-client <command> [<args>]

        The most commonly used commands are:
           init <path> <url>    Download the latest repository from an url to path
           checkout [-p <path>] Switch to latest version
           checkout <version> [-p <path>] Switch to a specified version
        ''')

        parser.add_argument("--debug", "-d", default='info', choices=['debug', 'info', 'warning', 'error'])

        subparsers = parser.add_subparsers(dest='command')

        parser_init = subparsers.add_parser("init")
        parser_init.add_argument("path")
        parser_init.add_argument("url")

        parser_checkout = subparsers.add_parser("checkout")
        parser_checkout.add_argument("version", nargs='?', default="latest")
        parser_checkout.add_argument("--path", "-p", default=os.getcwd())

        args = parser.parse_args()

        streamhandler = logging.StreamHandler(sys.stdout)
        streamhandler.setLevel(self.get_loglevel(args.debug))
        formatter = logging.Formatter('%(name)-20s - %(levelname)-5s - %(message)s')
        streamhandler.setFormatter(formatter)
        root.addHandler(streamhandler)

        if args.command == 'init':
            Repository.get_from_url(Path(args.path), args.url)
        elif args.command == 'checkout':
            repo = Repository(Path(args.path))

            if args.version == 'latest':
                repo.checkout_latest()
            else:
                repo.checkout_version(args.version)

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


if __name__ == '__main__':
    Client()
