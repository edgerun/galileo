import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

tests_require = [
    'redislite>=5.0.124623',
    'timeout_decorator>=0.4.1',
    'pytest>=5.0.0',
    'pytest-cov>=2.7.1',
    'coverage>=4.5.3',
    'coveralls'
]
install_requires = [
    'galileo-db>=0.10.1.dev4',
    'telemc>=0.3.0',
    'requests>=2.20.1',
    'redis>=3.2.1',
    'pymq>=0.4.0',
    'pyyaml>=5.4.1',
    'click>=7.0',
]

setuptools.setup(
    name="edgerun-galileo",
    version="0.10.0.dev3",
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
