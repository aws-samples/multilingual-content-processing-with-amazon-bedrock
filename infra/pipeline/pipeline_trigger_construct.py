# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing  import List
from pathlib import Path

from aws_cdk import (
    aws_lambda, aws_s3, aws_iam, aws_s3_notifications, Duration, 
    CustomResource
)
from aws_cdk.aws_ecr_assets import DockerImageAsset

from constructs import Construct
from aws_cdk.custom_resources import (
    Provider
)

class Trigger:
    S3 = 's3'

class PipelineTriggerConstruct(Construct):
    def __init__(
        self,
        scope  : Construct,
        id     : str,
        prefix : str,
        source : Path,
        common : dict,
        bucket : aws_s3.Bucket = None,
        **kwargs,
    ) -> None:

        super().__init__(scope = scope, id = id, **kwargs)

        self.__scope  = scope
        self.__prefix = prefix
        self.__source = source
        self.__common = common
        self.__bucket = bucket

        self.__trigger_lambdas = {}

        self.__trigger_lambdas[Trigger.S3] = self.__create_lambda_function(Trigger.S3, self.__common)

    def get_trigger_lambdas(self):

        return self.__trigger_lambdas

    def arm_s3_trigger(self):

        lambda_destination = aws_s3_notifications.LambdaDestination(
            self.__trigger_lambdas[Trigger.S3]
        )

        self.__bucket.add_event_notification(
            aws_s3.EventType.OBJECT_CREATED,
            lambda_destination,
            aws_s3.NotificationKeyFilter(prefix = 'acquire/')
        )

    def arm_s3_trigger_delayed(self):

        lambda_role = aws_iam.Role(
            scope      = self,
            id         = f'{self.__prefix}-srole-creator-trigger-s3',
            assumed_by = aws_iam.ServicePrincipal('lambda.amazonaws.com'),
        )

      # allow us to fetch worker template from s3 and call sagemaker APIs
        lambda_role.add_to_policy(
            statement = aws_iam.PolicyStatement(
                resources = ['*'],
                actions   = [
                    'lambda:InvokeFunction',
                    's3:*',
                    'sagemaker:*',
                    'logs:CreateLogGroup',
                    'logs:CreateLogStream',
                    'logs:PutLogEvents',
                ],
            )
        )

        lambda_path = str(Path(__file__).parent.joinpath('custom_resource_manager/').absolute())

        lambda_func = aws_lambda.Function(
            scope         = self,
            id            = f'{self.__prefix}-creator-trigger-s3',
            function_name = f'{self.__prefix}-creator-trigger-s3',
            code          = aws_lambda.Code.from_asset(lambda_path),
            handler       = 's3_trigger_manager.lambda_handler',
            runtime       = aws_lambda.Runtime.PYTHON_3_10,
            timeout       = Duration.minutes(15),
            memory_size   = 3000,
            role          = lambda_role,
        )

        provider = Provider(
            scope            = self,
            id               = f'{self.__prefix}-provider-trigger-s3',
            on_event_handler = lambda_func
        )

        trigger_resource = CustomResource(
            scope         = self,
            id            = f'{self.__prefix}-resource-trigger-s3',
            service_token = provider.service_token,
            properties    = {})

        trigger_resource.node.add_dependency(self.__bucket)

    def __create_lambda_function(self, trigger, environ):

        environment = dict(self.__common)
        environment.update(environ)


        lambda_function = aws_lambda.DockerImageFunction(
            scope         = self.__scope,
            id            = f'{self.__prefix}-trigger-{trigger}',
            function_name = f'{self.__prefix}-trigger-{trigger}',
            code          = aws_lambda.DockerImageCode.from_image_asset(
                directory=f'{self.__source}',
                file = "Dockerfile.trigger",
                build_args={
                    "STAGE": f'{trigger}'
                },
                asset_name= f'{self.__prefix}-docker-trigger-{trigger}'
            ),
            timeout       = Duration.minutes(15),
            architecture  = aws_lambda.Architecture.X86_64,
            memory_size   = 3000,
            environment   = environment
        )


        return lambda_function
