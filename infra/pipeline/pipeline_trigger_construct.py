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
