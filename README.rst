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

``ssmash`` is mainly intended for application developers who are at least partly
involved in the deployment and operations of their applications. If you want
to externalise (some of) the runtime configuration of your application, this
is a simple and cheap solution. If you also want to be able to automatically
restart your application when it's configuration changes, then this **is**
the tool for you


Installation
------------

Install ``ssmash`` using ``pip``, the standard python package installer:

.. code-block:: console

   $ pip install ssmash

You will probably use ``ssmash`` with the AWS command line tools, so install
and
`configure <https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html>`_
that too, if you haven't already:

.. code-block:: console

   $ pip install awscli
   $ aws configure


Example
-------

Suppose you have an input file like this:

.. code-block:: yaml

    acme:
        shipping-labels-service:
            enable-fast-delivery: true
            explosive-purchase-limit: 1000
            greeting: hello world
            whitelist-users:
                - coyote
                - roadrunner

Then run ``ssmash``:

.. code-block:: console

    $ ssmash -i acme_prod_config.yaml -o cloud_formation_template.yaml
    $ aws cloudformation deploy \
        --stack-name "acme-prod-config" --template-file cloud_formation_template.yaml \
        --no-fail-on-empty-changeset

You will now have the following parameters in AWS Systems Manager, that can
be loaded as a string inside your application:

* ``/acme/shipping-labels-service/enable-fast-delivery`` = "true"
* ``/acme/shipping-labels-service/explosive-purchase-limit`` = "1000"
* ``/acme/shipping-labels-service/greeting`` = "hello world"
* ``/acme/shipping-labels-service/whitelist-users`` = "coyote,roadrunner"


Automated Application Restarts
------------------------------

Most of the time, your application loads its configuration at startup.
Depending on your application, the safest and easiest way to reload its
configuration is to simply restart it.

ssmash has built-in support to restart some types of application as part of
the deployment process. We do this by telling it to "invalidate" the
configuration used by the application.

Docker with AWS ECS
^^^^^^^^^^^^^^^^^^^

``ssmash`` can generate CloudFormation that will safely restart the Tasks in
an ECS Service once your configuration has changed, and make the successful
deployment of your new application configuration depend upon the successful
restart of that Service. Just specify the target ECS service using extra
command line parameters, like so:

.. code-block:: console

    $ ssmash -i acme_prod_config.yaml -o cloud_formation_template.yaml \
        invalidate-ecs \
        --cluster-name acme-prod-cluster \
        --service-name shipping-labels-service \
        --role-name arn:aws:iam::123456789012:role/acme-ecs-admin
    $ aws cloudformation deploy \
        --stack-name "acme-prod-config" --template-file cloud_formation_template.yaml \
        --no-fail-on-empty-changeset

You can also refer to the name of a `CloudFormation Export
<https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-exports.html>`_
instead of using the name directly (eg. if your service has a non-obvious
generated name), using the interchangeable command line parameters for
``--cluster-import`` and ``--service-import`` and ``--role-import``.

Serverless with AWS Lambda
^^^^^^^^^^^^^^^^^^^^^^^^^^

``ssmash`` can generate CloudFormation that will safely cause your
serverless functions to discard their virtual machine (aka "`Execution Context
<https://docs.aws.amazon.com/lambda/latest/dg/running-lambda-code.html>`_"),
meaning they effectively reload their configuration. To
access this secret sauce, just add a couple more command line parameters:

.. code-block:: console

    $ ssmash -i acme_prod_config.yaml -o cloud_formation_template.yaml \
        invalidate-lambda \
        --function-name shipping-label-printer-function \
        --role-name arn:aws:iam::123456789012:role/acme-serverless-admin
    $ aws cloudformation deploy \
        --stack-name "acme-prod-config" --template-file cloud_formation_template.yaml \
        --no-fail-on-empty-changeset

You can also refer to the name of a `CloudFormation Export
<https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-exports.html>`_
instead of using the name directly, using the interchangeable command line
parameters for ``--function-import`` and ``--role-import``.


Advanced: Automated Restarts For Only Some Parameters
-----------------------------------------------------

Automated application restarts are great, but they don't scale when you have
a single configuration file that is used by multiple applications - you don't
want to restartevery application every time one of the config values changes.
Happily, ``ssmash`` can handle that too - you just need to invoke the magic
(madness!) of YAML tags, which allow us to add metadata to any part of the
configuration hierarchy (either leaf configuration values, or tree nodes).

First, let's extend the above example to include configuration for another
application:

.. code-block:: yaml

    acme:
        common:
            enable-slapstick: true
            region: us-west-2
        shipping-labels-service:
            enable-fast-delivery: true
            explosive-purchase-limit: 1000
            greeting: hello world
            whitelist-users:
                - coyote
                - roadrunner
        warehouse-service:
            item-substitutes:
                birdseed: "iron pellets"
                parachute: "backpack"

Now we add a special ``.ssmash-config`` key to tell ``ssmash`` how to restart
our applications. Then we annotate the configuration hierarchy using custom
YAML tags to tell ``ssmash`` which applications are invalidated by which parts
of the configuration hierarchy:

.. code-block:: yaml

    ---
    .ssmash-config:
        invalidations:
            # The dictionary key here ("shipping-labels") is used in the
            # configuration hierarchy to refer to this application
            shipping-labels: !ecs-invalidation
                # The `!ecs-invalidation` tag tells ssmash that this application
                # uses ECS, and the configuration fields correspond to those used
                # on the command line
                cluster_name: acme-prod-cluster
                service_name: shipping-label-service
                role_name: arn:aws:iam::123456789012:role/acme-ecs-admin
            warehousing: !ecs-invalidation
                cluster_name: acme-prod-cluster
                service_name: warehouse-service
                role_name: arn:aws:iam::123456789012:role/acme-ecs-admin
    acme:
        common:
            # This is a single leaf configuration value called "enable-slapstick",
            # which will cause both applications to restart when it is changed
            ? !item { invalidates: [ shipping-labels, warehousing ], key: enable-slapstick }
            : true
            region: us-west-2
        # This is a tree node called "shipping-labels-service", which will cause
        # the "shipping-labels" application defined above to restart when any of
        # it's configuration values are changed
        ? !item { invalidates: [ shipping-labels ], key: shipping-labels-service }
        :
            enable-fast-delivery: true
            explosive-purchase-limit: 1000
            greeting: hello world
            whitelist-users:
                - coyote
                - roadrunner
        # This is a tree node called "warehouse-service", which will cause
        # the "warehousing" application defined above to restart when any of
        # it's configuration values are changed
        ? !item { invalidates: [ warehousing ], key: warehouse-service }
        :
            item-substitutes:
                birdseed: "iron pellets"
                parachute: "backpack"


Then run ``ssmash`` normally:

.. code-block:: console

    $ ssmash -i acme_prod_config.yaml -o cloud_formation_template.yaml
    $ aws cloudformation deploy \
        --stack-name "acme-prod-config" --template-file cloud_formation_template.yaml \
        --no-fail-on-empty-changeset
