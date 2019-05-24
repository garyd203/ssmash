======
ssmash
======


.. image:: https://img.shields.io/pypi/v/ssmash.svg
        :target: https://pypi.python.org/pypi/ssmash

.. image:: https://img.shields.io/pypi/pyversions/ssmash.svg
        :target: https://pypi.python.org/pypi/ssmash
        :alt: Python versions

.. image:: https://readthedocs.org/projects/ssmash/badge/?version=latest
        :target: https://ssmash.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://img.shields.io/pypi/dm/ssmash.svg
        :target: https://pypi.python.org/pypi/ssmash
        :alt: Downloads

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
        :target: https://github.com/ambv/black
        :alt: Code style: black

`ssmash <https://ssmash.readthedocs.io>`_, the SSM AppConfig Storage Helper,
is an easy-to-use application configuration management tool for AWS
deployments. You specify hierarchical configuration values in a simple YAML
file, and ``ssmash`` will turn that into an AWS CloudFormation file that
stores your configuration values in the SSM Parameter Store.

Installation
------------

Install ``ssmash`` using ``pip``, the standard python package installer:

.. code-block:: console

   $ pip install ssmash

Example
-------

Suppose you have an input file like this:

.. code-block:: yaml

    acme:
        shipping-labels-service:
            block-coyotes: true
            explosive-purchase-limit: 1000
            greeting: hello world

Then run ``ssmash``:

.. code-block:: console

    $ ssmash acme_prod_config.yaml cloud_formation_template.yaml
    $ aws cloudformation deploy \
        --stack-name "acme-prod-config" --template-file cloud_formation_template.yaml \
        --no-fail-on-empty-changeset

You will now have the following parameters in AWS Systems Manager, that can
be loaded as a string inside your application:

* ``/acme/shipping-labels-service/block-coyotes`` = "true"
* ``/acme/shipping-labels-service/explosive-purchase-limit`` = "1000"
* ``/acme/shipping-labels-service/greeting`` = "hello world"


