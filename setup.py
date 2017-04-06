from distutils.core import setup

from setuptools import find_packages

setup(
    # Application name:
    name="BiReUS",

    # Version number (initial):
    version="0.1.0",

    # Application author details:
    author="Christian Schmidt",
    author_email="c-schmidt@gmx.eu",

    # Packages
    packages=find_packages(),

    # Include additional files into the package
    include_package_data=True,

    # Details
    url="https://github.com/Brutus5000/BiReUS",

    license=open("LICENSE").read(),
    description="BiReUS is a tool to create and apply binary patches for application data (versions forward and optional backward) based on the bsdiff algorithm.",

    long_description=open("README.md").read(),

    # Dependent packages (distributions)
    install_requires=[
        "bsdiff4", "aiohttp", "networkx"
    ],
)
