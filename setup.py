import os

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements-dev.txt", "r") as fh:
    tests_require = [line for line in fh.read().split(os.linesep) if line]

with open("requirements.txt", "r") as fh:
    install_requires = [line for line in fh.read().split(os.linesep) if line and not line.startswith('git')]

setuptools.setup(
    name="edgerun-galileo",
    version="0.6.0.dev1",
    author="Thomas Rausch",
    author_email="t.rausch@dsg.tuwien.ac.at",
    description="Galileo: A framework for distributed load testing experiments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/edgerun/galileo",
    packages=setuptools.find_packages(),
    test_suite="tests",
    tests_require=tests_require,
    install_requires=install_requires,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": ['galileo = galileo.cli.galileo:main']
    },
)
