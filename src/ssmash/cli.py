# -*- coding: utf-8 -*-

"""Convert a plain YAML file with application configuration into a CloudFormation template with SSM parameters."""

import sys

import click
from datetime import datetime, timezone
import yaml
from flyingcircus.core import Stack

from ssmash.converter import convert_hierarchy_to_ssm


@click.command(help=__doc__)
@click.argument("input", type=click.File("r"), default="-")
@click.argument("output", type=click.File("w"), default="-")
def create_stack(input, output):
    # Load source config
    #
    # Note that PyYAML returns None for an empty file, rather than an empty
    # dictionary
    appconfig = yaml.safe_load(input)
    if appconfig is None:
        appconfig = {}

    # Create stack
    stack = Stack(Description="")  # FIXME desc

    from . import __version__

    stack.Metadata["ssmash"] = {
        "generated_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "version": __version__,
    }

    # Create a parameter for each element in the config hierarchy.
    convert_hierarchy_to_ssm(appconfig, stack)

    # Write YAML to the specified file
    output.write(stack.export("yaml"))


if __name__ == "__main__":
    sys.exit(create_stack())
