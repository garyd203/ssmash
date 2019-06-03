"""Functions to create Custom Resources in Cloud Formation"""


# NB: Don't put imports here for Lambda function handlers. They should be self-contained


# TODO tests


def restart_ecs_service_resource_handler(event, context):
    """Lambda handler function to restart an ECS service, as a CloudFormation resource.

    This is intended to be used in an inline deployment. The physical ID is
    the ID of the ECS service deployment
    """
    # TODO consider bringing the `cfnresponse` module in locally as a pseudo-dependency, so that we can reference it.
    # The `cfnresponse` module is injected at runtime if you are executing a Custom Resource handler
    # noinspection PyUnresolvedReferences
    import cfnresponse

    import logging

    logging.basicConfig(level=logging.DEBUG)
    LOGGER = logging.getLogger("restarter")  # TODO
    try:
        import boto3

        # TODO is there a way to make this idempotent on event["RequestId"]? OR just hope it only gets called once...

        ecs = boto3.client("ecs")
        response = {}
        physical_id = event.get("PhysicalResourceId")

        if event["RequestType"] in ["Create", "Update"]:
            # Restart the ECS service
            #   FIXME this breaks if multiple restarts get scheduled
            # FIXME Not sure how best to deal with timeouts... don't forget context.get_remaining_time_in_millis()
            properties = event["ResourceProperties"]
            update_result = ecs.update_service(
                cluster=properties["ClusterArn"],
                service=properties["ServiceArn"],
                forceNewDeployment=True,
            )

            # Get the deployment ID, which is first in the list. TODO pluck out newest using deployment["createdAt"]
            deployment = update_result["service"]["deployments"][0]
            # assert deployment["status"] == "PRIMARY" #TODO real error or don't bother
            physical_id = deployment["id"]

            # Poll until the ECS service reaches a steady state
            ecs.get_waiter("services_stable").wait(
                cluster=properties["ClusterArn"],
                services=[properties["ServiceArn"]],
                # TODO use WaiterConfig to timeout inside out expected timeout
            )

            # FIXME check result from ecs waiter
        elif event["RequestType"] == "Delete":
            # Doesn't make any sense to delete an ECS deployment - just return
            LOGGER.info(
                "Ignoring request to delete resource for deployment %s", physical_id
            )
        else:
            raise ValueError("Unknown CloudFormation request type")
        cfnresponse.send(event, context, cfnresponse.SUCCESS, response, physical_id)
        # TODO notify (optional) CFN waiter
    except Exception as ex:
        LOGGER.exception("argh!")  # TODO
        # FIXME the cfnresponse module doesn't let us set the `Reason` in the response
        # TODO set PhysicalResourceId in response if known. at least dont let it use the default log stream name (!)
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
