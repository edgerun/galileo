import os

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements-dev.txt", "r") as fh:
    tests_require = [line for line in fh.read().split(os.linesep) if line]

with open("requirements.txt", "r") as fh:
    install_requires = [line for line in fh.read().split(os.linesep) if line and not line.startswith('git')]

setuptools.setup(
    name="mc2-galileo",
    version="0.4.0",
    author="Thomas Rausch",
    author_email="t.rausch@dsg.tuwien.ac.at",
    description="Galileo: Experimentation and Analytics Framework for MC2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://git.dsg.tuwien.ac.at/mc2/galileo",
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
