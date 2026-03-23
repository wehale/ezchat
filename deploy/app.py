#!/usr/bin/env python3
"""CDK app entry point for kirbus infrastructure."""
import aws_cdk as cdk

from kirbus_stack import KirbusStack

app = cdk.App()
KirbusStack(app, "KirbusStack",
    env=cdk.Environment(
        account="417079469462",
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)
app.synth()
