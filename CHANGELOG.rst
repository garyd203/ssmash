=========
Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.


[Unreleased]
------------

Changed
~~~~~~~
* `#22 <https://github.com/garyd203/ssmash/issues/22>`_ : Change command line
  API so that input is required, and output is an option instead of an
  argument

v1.1.0 (2019-06-05)
-------------------

Added
~~~~~
* Be able to automatically invalidate an existing ECS Service as part of the
  parameter deployment, so that it picks up the new configuration.

v1.0.0 (2019-05-30)
-------------------

v1.0.0-rc1 (2019-05-24)
-----------------------

Added
~~~~~
* ``ssmash`` script to create String SSM Parameters from a simple config file stored in YAML
* Basic documentation in README

v0.1.0 (2019-05-14)
-------------------

Added
~~~~~
* First release on PyPI.
* Cookiecutter skeleton only, no functionality
