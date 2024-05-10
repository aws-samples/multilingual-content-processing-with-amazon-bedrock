# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing  import List, Dict
from pathlib import Path

from aws_cdk import (
    aws_lambda, Duration
)
from aws_cdk.aws_ecr_assets import DockerImageAsset
from constructs import Construct

class Manager:
    STARTUP = 'startup'
    PROMOTE = 'promote'
    BREAKUP = 'breakup'
    RESTART = 'restart'
    PROCESS = 'process'
    CHECKUP = 'checkup'
    STANDBY = 'standby'

class PipelineManagerConstruct(Construct):
    def __init__(
        self,
        scope  : Construct,
        id     : str,
        prefix : str,
        source : Path,
        common : Dict,
        **kwargs,
    ) -> None:

        super().__init__(scope = scope, id = id, **kwargs)

        self.__scope  = scope
        self.__prefix = prefix
        self.__source = source
        self.__common = common

        self.__manager_lambdas = {}

        self.__create_startup_lambda()
        self.__create_breakup_lambda()
        self.__create_restart_lambda()
        self.__create_promote_lambda()

    def get_manager_lambdas(self):
        """
        Returns constructed management lambda functions
        {
            'restart' : aws_lambda.Function
            'startup' : aws_lambda.Function
            'breakup' : aws_lambda.Function
            'promote' : aws_lambda.Function
        }
        """

        return self.__manager_lambdas

    def __create_startup_lambda(self):

        self.__manager_lambdas[Manager.STARTUP] = self.__create_lambda_function(Manager.STARTUP, {})

    def __create_breakup_lambda(self):

        self.__manager_lambdas[Manager.BREAKUP] = self.__create_lambda_function(Manager.BREAKUP, {})

    def __create_restart_lambda(self):
        self.__manager_lambdas[Manager.RESTART] = self.__create_lambda_function(Manager.RESTART, {})

    def __create_promote_lambda(self):
        self.__manager_lambdas[Manager.PROMOTE] = self.__create_lambda_function(Manager.PROMOTE, {})

    def __create_lambda_function(self, manager, environ):

        environment = dict(self.__common)
        environment.update(environ)

        # docker_image = DockerImageAsset(self, f'{self.__prefix}-docker-manager-{manager}',
        #     directory=f'{self.__source}',
        #     file = "Dockerfile.manager",
        #     build_args={
        #         "STAGE": manager,
        #     })


        lambda_function = aws_lambda.DockerImageFunction(
            scope         = self.__scope,
            id            = f'{self.__prefix}-manager-{manager}',
            function_name = f'{self.__prefix}-manager-{manager}',
            code          = aws_lambda.DockerImageCode.from_image_asset(
                directory=f'{self.__source}',
                file = "Dockerfile.manager",
                build_args={
                    "STAGE": manager,
                },
                asset_name= f'{self.__prefix}-docker-manager-{manager}'
            ),
            timeout       = Duration.minutes(15),
            architecture  = aws_lambda.Architecture.X86_64,
            memory_size   = 3000,
            environment   = environment
        )

        return lambda_function
