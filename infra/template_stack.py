# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_cdk import (
    Stack,
    aws_s3,
    aws_s3_deployment,
    RemovalPolicy,
    DockerImage,
    aws_iam,
    Aws
)
from cdk_nag import  NagSuppressions

from constructs import Construct
from pathlib import Path



class TemplateStack(Stack):

    def __init__(
            self,
            scope  : Construct,
            id     : str,
            prefix : str,
            suffix : str,
            source : Path,
            bucket : aws_s3.Bucket = None,
            **kwargs
    ) -> None:

        super().__init__(scope, id, **kwargs)

        self.__prefix = prefix
        self.__suffix = suffix
        self.__source = source

        self.__bucket_name = f'{self.__prefix}-store-resource-{self.__suffix}'


        self.__bucket = aws_s3.Bucket(
            scope                    = self,
            id                       = self.__bucket_name,
            bucket_name              = self.__bucket_name,
            block_public_access      = aws_s3.BlockPublicAccess.BLOCK_ALL,               
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            enforce_ssl=True
        )


        # this prefix is used to generate liquid {{ s3://... | grant_read_access }} tags inside
        # the worker template during the 'npm run build-hitl' step.

        self.__assets_path = f'.assets/{self.__source.name}'
        self.__assets_uri  = f's3://{self.__bucket_name}/{self.__assets_path}'

        print(self.__assets_uri)

        environ = {
            'S3_PREFIX' : self.__assets_uri,
        }

        bundler = {
            'image'      : DockerImage.from_registry('node:16.14.2'),
            'user'       : 'node',
            'environment': environ,
            'command'    :
            [
                'bash',
                '-c',
                '&&'.join(
                    [
                        'npm install',
                        'npm run build-hitl',
                        'mkdir -p /asset-output',
                        'cp -R build/* /asset-output/',
                    ]
                ),
            ],
        }

        self.__assets_bundle = aws_s3_deployment.Source.asset(
            path     = str(source),
            bundling = bundler
        )

        # deploy the worker template bundle to s3
        aws_s3_deployment.BucketDeployment(
            scope                  = self,
            id                     = f'{self.__prefix}-{self.__source.name}-deploy',
            sources                = [self.__assets_bundle],
            destination_bucket     = self.__bucket,
            destination_key_prefix = self.__assets_path,
        )

    def get_resources(self):
        """
        all resources other stacks might be interested in leveraging
        """

        return {
            'liquid_uri' : f'{self.__assets_uri}/worker-template.liquid.html'
        }

    @property
    def bucket_name(self) -> str:
        return self.__bucket.bucket_name