#!/usr/bin/env python3
"""Bidirectional Repository Update Service - server component"""
import argparse
import logging
import os
import sys

from server.repository_manager import RepositoryManager

root = logging.getLogger()
root.setLevel(logging.DEBUG)


class Server(object):
    def __init__(self):
        parser = argparse.ArgumentParser(
            description="BiReUS (Bidirectional Repository Update Service) - server component")
        parser.add_argument('-p', '--path', dest="path", help='file path to the repositories')
        parser.add_argument('-c', '--cleanup', dest="cleanup", action="store_true",
                            help='cleanup and remove all existing patches')
        parser.add_argument('-fo', '--forward-only', dest="forward_only", action="store_true",
                            help='skip creation of backward-patches')
        parser.add_argument("--debug", "-d", default='info', choices=['debug', 'info', 'warning', 'error'])

        args = parser.parse_args()
        abspath = os.path.abspath(args.path)

        streamhandler = logging.StreamHandler(sys.stdout)
        streamhandler.setLevel(self.get_loglevel(args.debug))
        formatter = logging.Formatter('%(name)-25s - %(levelname)-5s - %(message)s')
        streamhandler.setFormatter(formatter)
        root.addHandler(streamhandler)

        if os.path.exists(args.path):
            os.chdir(args.path)
        else:
            argparse.ArgumentError("-p", "is not a valid path")
            exit()

        repoManager = RepositoryManager(abspath)

        if args.cleanup:
            repoManager.full_cleanup()

        repoManager.full_update(args.forward_only)

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
