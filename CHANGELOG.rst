=========
Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

v2.1.2 (2019-12-30)
-------------------

Fixed:
* `#39 <https://github.com/garyd203/ssmash/issues/39>`_ : Fix PyYAML
  version inconsistency that prevents installation with `pip`. Thanks
  to `@NeolithEra <https://github.com/NeolithEra>`_ for the bug report.

v2.1.1 (2019-11-29)
-------------------

Fixed:
* Update versions for dependencies

v2.1.0 (2019-11-28)
-------------------

Added:

* Be able to invalidate a single Lambda Function

Fixed:
* Update versions for dependencies to be "compatible"

v2.0.1 (2019-06-28)
-------------------

Fixed:

* Couldn't run script

v2.0.0 (2019-06-28)
-------------------

Changed:

* `#22 <https://github.com/garyd203/ssmash/issues/22>`_ : Change command line
  API so that the input and output files are options, rather than arguments.
* `#22 <https://github.com/garyd203/ssmash/issues/22>`_ : Change command line
  API so that invalidating an ECS Service is done through a chained
  sub-command, rather than additional options.

Added:

* `#8 <https://github.com/garyd203/ssmash/issues/8>`_ : Support lists of plain
  values, which are stored as a SSM StringList parameter

Removed:

* You can't specify input and output files as positional arguments any more.
  Use `--input-file FILENAME` and `--output-file FILENAME` instead.
* The `--invalidate-ecs-service` and `--invalidation-role` options have been
  replaced with the `invalidate-ecs` command.

v1.1.0 (2019-06-05)
-------------------

Added:

* Be able to automatically invalidate an existing ECS Service as part of the
  parameter deployment, so that it picks up the new configuration.

v1.0.0 (2019-05-30)
-------------------

v1.0.0-rc1 (2019-05-24)
-----------------------

Added:

* ``ssmash`` script to create String SSM Parameters from a simple config file stored in YAML
* Basic documentation in README

v0.1.0 (2019-05-14)
-------------------

Added:

* First release on PyPI.
* Cookiecutter skeleton only, no functionality
