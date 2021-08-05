import pathlib

from setuptools import setup, find_packages
from setuptools.command.install import install

##########################################à

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="modern-mafia",
    version="0.0.0.1",
    description="description",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/mattyonweb/<name>",
    author="Jacopo Belbo",
    author_email="cvd00@insicuri.net",
    license="GNU General Public License v3.0",
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3.9",
    ],
    packages=find_packages(),
    install_requires=[
        "networkx", "matplotlib", 
        # external libraries to automatically download before a pip-install
    ],
    include_package_data=True, #TODO?
    # cmdclass={ #specifica azioni da intraprendere post-installazione
    #     'develop': PostDevelopCommand,
    #     'install': PostInstallCommand,
    # },
    entry_points={
        "console_scripts": [
            "moder-mafia=ndrangheta.graph:play",
        ]
    },
    python_requires='>=3.9',
)
