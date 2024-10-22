#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks, NagSuppressions

from pathlib      import Path

from infra.standard_utils import Env
from infra.template_stack import TemplateStack # worker template resource
from infra.pipeline_stack import PipelineStack

prefix = Env.GetPrefix()
suffix = Env.GetSuffix()

if __name__ == '__main__':

    app = cdk.App()

    # Define your stacks
    template_stack = TemplateStack(
        scope=app,
        id=f'{prefix}-Template',
        prefix=prefix,
        suffix=suffix,
        source=Path('source/augment-ui').absolute()
    )
    
    NagSuppressions.add_resource_suppressions(
        template_stack,
        [
            {
                "id": "AwsSolutions-S1",
                "reason": "Server access logs are not required for this S3 bucket as it is used for demo purposes."
            },
            {
                "id": "AwsSolutions-IAM4",
                "reason": "Using AWS managed policies for Lambda is acceptable for this demo use case."
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "Wildcard permissions on S3 resources are used by BucketDeploy managed policy."
            },
            {
                "id": "AwsSolutions-L1",
                "reason": "The Lambda runtime version is acceptable for this demo, but in production, the latest version should be used."
            }
        ],
        apply_to_children=True 
    )

    resource_bucket_name = template_stack.bucket_name

    pipeline_stack = PipelineStack(
        scope=app,
        id=f'{prefix}-Pipeline',
        prefix=prefix,
        suffix=suffix,
        resource_bucket_name=resource_bucket_name,
        source=Path('source/lambdas').absolute(),
        liquid=template_stack.get_resources()['liquid_uri']
        # liquid = None
    )
    
    NagSuppressions.add_resource_suppressions(
        pipeline_stack,
        [
            {
                "id": "AwsSolutions-S1",
                "reason": "Server access logs are not required for this S3 bucket as it is used for demo purposes."
            },
            {
                "id": "AwsSolutions-DDB3",
                "reason": "Point-in-time recovery is not enabled as it is not required for this demo scenario."
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "Wildcard permissions are for objects in the specific bucket. <mcpstoredocument965637542341F121B3BC>/*"
            },
            {
                "id": "AwsSolutions-L1",
                "reason": "The Lambda runtime version is sufficient for this use case. Upgrading is not needed."
            },
            {
                "id": "AwsSolutions-IAM4",
                "reason": "AWSLambdaBasicExecutionRole uses managed policies that is limited to invoking lambda."
            },
            {
                "id": "AwsSolutions-SQS3",
                "reason": "This queue does not require a DLQ for the current use case."
            }
        ],
        apply_to_children=True 
    )

    # Set stack dependencies
    pipeline_stack.add_dependency(template_stack)

    # Apply CDK Nag checks to all stacks
    cdk.Aspects.of(app).add(AwsSolutionsChecks())


    app.synth()
