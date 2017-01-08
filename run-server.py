#!/usr/bin/env python3
"""Bidirectional Repository Update Service - server component"""
import argparse
import logging
import os
import sys

from server.repository_manager import RepositoryManager

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)-25s - %(levelname)-5s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

parser = argparse.ArgumentParser(description="BiReUS (Bidirectional Repository Update Service) - server component")
parser.add_argument('-p', '--path', dest="path", help='file path to the repositories')
parser.add_argument('-c', '--cleanup', dest="cleanup", action="store_true",
                    help='cleanup and remove all existing patches')
parser.add_argument('-fo', '--forward-only', dest="forward_only", action="store_true",
                    help='skip creation of backward-patches')

if __name__ == '__main__':
    args = parser.parse_args()

    abspath = os.path.abspath(args.path)
    if os.path.exists(args.path):
        os.chdir(args.path)
    else:
        argparse.ArgumentError("-p", "is not a valid path")
        exit()

    repoManager = RepositoryManager(abspath)

    if args.cleanup:
        repoManager.full_cleanup()

    repoManager.full_update(args.forward_only)
