# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing  import List
from pathlib import Path
from boto3   import client
import os
import subprocess

from aws_cdk import (
    aws_sqs, aws_lambda, aws_sns, aws_iam, aws_events, 
    aws_events_targets, Aws, Duration,  aws_iam as iam
)

from aws_cdk.aws_ecr_assets import DockerImageAsset

from constructs import Construct

from .a2i_workflow_construct import A2IWorkflowConstruct
from .a2i_template_construct import A2ITemplateConstruct

class Process:
    ACQUIRE = 'acquire'
    AUGMENT = 'augment'
    CATALOG = 'catalog'
    CONVERT = 'convert'
    EXTRACT = 'extract'
    OPERATE = 'operate'
    RESHAPE = 'reshape'

class Aspect:
    BEGIN = 'begin'
    ACTOR = 'actor'
    AWAIT = 'await'

class PipelineProcessConstruct(Construct):

    def __init__(
        self,
        scope  : Construct,
        id     : str,
        prefix : str,
        common : dict,
        source : Path,
        liquid,
        bucket,
        document_bucket_name,
        resource_bucket_name,
        **kwargs,
    ) -> None:

        super().__init__(scope = scope, id = id, **kwargs)

        self.__scope  = scope
        self.__prefix = prefix

        self.__common = common
        self.__source = source
        self.__document_bucket_name = document_bucket_name
        self.__resource_bucket_name = resource_bucket_name
        self.__bucket = bucket
        self.__liquid = liquid

        self.__stage_queues = {}
        self.__stage_topics = {}
        self.__stage_begin_lambdas = {}
        self.__stage_actor_lambdas = {}
        self.__stage_await_lambdas = {}

        
        self.__create_stage_extract(stage = Process.EXTRACT)
        self.__create_stage_operate(stage = Process.OPERATE)
        self.__create_stage_reshape(stage = Process.RESHAPE)
        self.__create_stage_augment(stage = Process.AUGMENT)
        self.__create_stage_catalog(stage = Process.CATALOG)

    def get_stage_actor_lambdas(self):
        """
        Returns the constructed lambda functions
        Example Returned object (These are the Async Lambda Functions)
        {
            'acquire'    : aws_lambda.Function
            'augment'    : aws_lambda.Function
            'catalog'    : aws_lambda.Function
            .
            .
        }
        """

        return self.__stage_actor_lambdas

    def get_stage_await_lambdas(self):
        """
        Returns the constructed lambda functions
        Example Returned object (These are the Await Lambda Functions)
        {
            'acquire' : aws_lambda.Function
            'augment' : aws_lambda.Function
            'catalog' : aws_lambda.Function
            .
            .
        }
        """

        return self.__stage_await_lambdas

    def get_stage_begin_lambdas(self):
        """
        Returns the constructed lambda functions
        Example Returned object (These are the Begin Lambda Functions)
        {
            'acquire' : aws_lambda.Function
            'augment' : aws_lambda.Function
            'catalog' : aws_lambda.Function
            .
            .
        }
        """

        return self.__stage_begin_lambdas

    def __get_work_teams(self):
        sagemaker = client("sagemaker")
        paginator = sagemaker.get_paginator("list_workteams")
        workteams = set()
        for page in paginator.paginate():
            for workteam in page["Workteams"]:
                workteams.add(workteam["WorkteamName"])

        return workteams



    def __create_stage_augment(self, stage):

        queue = self.__create_queue(stage)

        self.__create_actor_lambda(stage, queue)
        self.__create_begin_lambda(stage, queue)
        self.__create_await_lambda(stage, queue)

        template_resource = A2ITemplateConstruct(
            scope         = self,
            prefix        = self.__prefix,
            template_name = f'{self.__prefix}-a2i-template',
            template_path = self.__liquid,
            bucket_name = self.__resource_bucket_name
        )

        commons = self.node.try_get_context('ENVIRONMENTS')

        if  len(commons['WORK_TEAM_NAMES']) == 0:
            raise Exception('Make sure you have have added created work team name in the cdk.json: ENVIRONMENTS')

        allowed_workflow_resource_arns = []
        work_teams = self.__get_work_teams()

        for workteam in commons['WORK_TEAM_NAMES']:
            if workteam not in work_teams :
                raise Exception(f'Work team : {workteam} you have added does not exist in your account Make sure to '
                                'create work team from aws console.')

            workteam_arn = f'arn:aws:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:workteam/private-crowd/{workteam}'

          # Custom HumanReview Workflow Resource
            workflow_resource = A2IWorkflowConstruct(
                scope             = self,
                workflow_name     = f'{self.__prefix}-wflow-{workteam}',
                s3_output_path    = self.__bucket.s3_url_for_object(f'augment/.a2i'),
                prefix            = self.__prefix,
                template_resource = template_resource,
                document_bucket_name       = self.__document_bucket_name,
                resource_bucket_name       = self.__resource_bucket_name,
                workteam_arn      = workteam_arn,
                task_count        = 1,
                task_description  = f'Review Tables from Source Document - {workteam.title()}',
                task_title        = f'Document Review'
            )

            allowed_workflow_resource_arns.append(workflow_resource.get_workflow_arn())

            self.__stage_begin_lambdas[Process.AUGMENT].add_environment(
                f'WFLOW_A2I_{workteam.upper()}_ARN', workflow_resource.get_workflow_arn()
            )

        self.__stage_begin_lambdas[Process.AUGMENT].role.add_to_policy(
            statement = aws_iam.PolicyStatement(
                effect    = aws_iam.Effect.ALLOW,
                actions   = ['sagemaker:ListHumanLoops',
                             'sagemaker:StartHumanLoop',
                             'sagemaker:StopHumanLoop'],
                resources=[f'arn:aws:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:*']
            )
        )

        human_review_event_pattern = aws_events.EventPattern(
            source      = ['aws.sagemaker'],
            detail_type = ['SageMaker A2I HumanLoop Status Change'],
            detail     = {
                'flowDefinitionArn': allowed_workflow_resource_arns
            }
        )

        rule = aws_events.Rule(scope         = self,
                               id            = f'{self.__prefix}-human-review-complete',
                               event_pattern = human_review_event_pattern)
        
        rule.add_target(target = aws_events_targets.SqsQueue(queue = queue))
    
        

    def __create_stage_catalog(self, stage):

        queue = self.__create_queue(stage)

        self.__create_actor_lambda(stage, queue)
        self.__create_begin_lambda(stage, queue)
        self.__create_await_lambda(stage, queue)


    def __create_stage_extract(self, stage):

        queue = self.__create_queue(stage)

        self.__create_actor_lambda(stage, queue)
        self.__create_begin_lambda(stage, queue)
        self.__create_await_lambda(stage, queue)
   
        self.__srole_bedrock = aws_iam.Role(
            scope      = self,
            id         = f'{self.__prefix}-srole-bedrock',
            assumed_by = aws_iam.ServicePrincipal('bedrock.amazonaws.com') 
        )
        
        self.__srole_bedrock.grant_pass_role(self.__stage_actor_lambdas[Process.EXTRACT])

        self.__stage_actor_lambdas[Process.EXTRACT].role.add_to_policy(
            statement = aws_iam.PolicyStatement(
                effect    = aws_iam.Effect.ALLOW,
                actions   = ["bedrock:InvokeModel"],
                resources=[f'arn:aws:bedrock:{Aws.REGION}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0',]
            )
        )



    def __create_stage_operate(self, stage):

        queue = self.__create_queue(stage)

        self.__create_actor_lambda(stage, queue)
        self.__create_begin_lambda(stage, queue)
        self.__create_await_lambda(stage, queue)

    def __create_stage_reshape(self, stage):

        queue = self.__create_queue(stage)

        self.__create_actor_lambda(stage, queue)
        self.__create_begin_lambda(stage, queue)
        self.__create_await_lambda(stage, queue)

    def __create_queue(self, stage):

        self.__stage_queues[stage] = aws_sqs.Queue(

            scope      = self.__scope,
            id         = f'{self.__prefix}-queue-{stage}',
            queue_name = f'{self.__prefix}-queue-{stage}',
            enforce_ssl=True
        )

        return self.__stage_queues[stage]

    def __create_topic(self, stage):

        self.__stage_topics[stage] = aws_sns.Topic(
            scope      = self,
            id         = f'{self.__prefix}-topic-{stage}',
            topic_name = f'{self.__prefix}-topic-{stage}'
        )

        return self.__stage_topics[stage]

    def __create_begin_lambda(self, stage, queue):

        actor = self.__stage_actor_lambdas[stage]


        environ = {
            'STAGE'       : stage,
            'STAGE_QUEUE' : queue.queue_name,
        }

        lambda_function = self.__create_lambda_function(stage, Aspect.BEGIN, environ)
        queue.grant_send_messages(lambda_function)

      # Grant IAM Permission to begin lambda to execute actor lambda
        actor.grant_invoke(lambda_function)

        self.__stage_begin_lambdas[stage] = lambda_function

    def __create_actor_lambda(self, stage, queue):

        environ = {
            'STAGE'       : stage,
            'STAGE_QUEUE' : queue.queue_name,
        }

        lambda_function = self.__create_lambda_function(stage, Aspect.ACTOR, environ)

        queue.grant_send_messages(lambda_function)

        self.__stage_actor_lambdas[stage] = lambda_function

    def __create_await_lambda(self, stage, queue):

        environ = {
            'STAGE'       : stage,
            'STAGE_QUEUE' : queue.queue_name,
        }

        lambda_function = self.__create_lambda_function(stage, Aspect.AWAIT, environ)

        queue.grant_consume_messages(lambda_function)
        queue.grant(lambda_function, "sqs:*")

        self.__stage_await_lambdas[stage] = lambda_function




    def __create_lambda_function(self, stage, aspect, environ):

        environment = self.__common.copy()
        environment.update(environ)


        lambda_function = aws_lambda.DockerImageFunction(
            scope         = self.__scope,
            id            = f'{self.__prefix}-processor-{stage}-{aspect}',
            function_name = f'{self.__prefix}-processor-{stage}-{aspect}',
            code          = aws_lambda.DockerImageCode.from_image_asset(
                directory=f'{self.__source}',
                build_args={
                    "STAGE": stage,
                    "ASPECT": aspect,
                },
                asset_name = f'{self.__prefix}-docker-{stage}-{aspect}'
            ),
            timeout       = Duration.minutes(15),
            architecture  = aws_lambda.Architecture.X86_64,
            memory_size   = 3000,
            environment   = environment
        )

        return lambda_function
