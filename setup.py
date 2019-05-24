#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("CHANGELOG.rst") as history_file:
    history = history_file.read()

requirements = ["Click>=6.0", "PyYAML==5.1", "flying-circus==0.6.3", "inflection==0.3.1"]

setup_requirements = ["pytest-runner"]

test_requirements = ["pytest"]

setup(
    author="Gary Donovan",
    author_email="gazza@gazza.id.au",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development",
        "Topic :: System :: Systems Administration",
    ],
    description="SSM AppConfig Storage Helper",
    entry_points={"console_scripts": ["ssmash=ssmash.cli:create_stack"]},
    install_requires=requirements,
    license="GNU Affero General Public License v3",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="ssmash application-configuration configuration AWS cloudformation infrastructure-as-code",
    metadata_version="2.1",
    name="ssmash",
    package_dir={"": "src"},
    packages=find_packages(where="src", include=["ssmash"]),
    project_urls={
        "Documentation": "https://ssmash.readthedocs.io/en/latest/",
        "Source": "https://github.com/garyd203/ssmash",
        "Tracker": "https://github.com/garyd203/ssmash/issues",
    },
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/garyd203/ssmash",
    version="1.0.0-rc1",
    zip_safe=False,
)
