#!/usr/bin/env python3
"""Bidirectional Repository Update Service - server component"""
import argparse
import logging
import os
import sys
from pathlib import Path

from server.repository_manager import RepositoryManager

root = logging.getLogger()
root.setLevel(logging.DEBUG)


class Server(object):
    def __init__(self):
        parser = argparse.ArgumentParser(
            description="BiReUS (Bidirectional Repository Update Service) - server component")

        parser.add_argument("--debug", "-d", default='info', choices=['debug', 'info', 'warning', 'error'])

        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = True

        parser_add = subparsers.add_parser("add")
        parser_add.add_argument("name", help="name of the repository")
        parser_add.add_argument("--first-version", "-fv", default="1.0.0", help="name of the initial version")
        parser_add.add_argument("--mode", "-m", default="bi", help="update mode")
        parser_add.add_argument("--path", "-p", default=os.getcwd(), help="repository root path")

        parser_update = subparsers.add_parser("update")
        parser_update.add_argument("--repo", "-r", nargs="?", default=None)
        parser_update.add_argument("--cleanup", "-c", dest="cleanup", action="store_true",
                                   help='cleanup and remove all existing patches')
        parser_update.add_argument("--path", "-p", default=os.getcwd(), help="repository root path")

        args = parser.parse_args()
        abspath = Path(args.path)

        streamhandler = logging.StreamHandler(sys.stdout)
        streamhandler.setLevel(self.get_loglevel(args.debug))
        formatter = logging.Formatter('%(name)-25s - %(levelname)-5s - %(message)s')
        streamhandler.setFormatter(formatter)
        root.addHandler(streamhandler)

        if not abspath.exists():
            argparse.ArgumentError("-p", "is not a valid path")
            exit()

        repo_manager = RepositoryManager(Path(args.path))

        if args.command == "add":
            repo_manager.create(args.name, args.first_version, args.mode)
            print("Repository %s created, copy your content into %s and run update" % (
            args.name, str(Path(args.path, args.first_version))))

        elif args.command == "update":
            if args.cleanup:
                repo_manager.full_cleanup()

            repo_manager.full_update()

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
    Server()
