import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mc2-galileo",
    version="0.0.1",
    author="Thomas Rausch",
    author_email="t.rausch@dsg.tuwien.ac.at",
    description="Galileo: Experimentation and Analytics Framework for MC2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://git.dsg.tuwien.ac.at/mc2/galileo",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
#    entry_points={
#        "console_scripts": ['symmetry = symmetry.cli.symmetry:main']
#    },

)
