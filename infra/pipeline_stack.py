# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_cdk import (
    aws_s3, aws_lambda, aws_dynamodb, Stack, RemovalPolicy, 
    BundlingOptions,  Aws, DockerImage

)

from constructs import Construct
from pathlib import Path
import docker

from .pipeline.pipeline_process_construct import PipelineProcessConstruct
from .pipeline.pipeline_manager_construct import PipelineManagerConstruct
from .pipeline.pipeline_trigger_construct import PipelineTriggerConstruct
from .pipeline.pipeline_machine_construct import PipelineMachineConstruct
from .shared.s3_custom_bucket_construct import S3CustomBucketConstruct


class PipelineStack(Stack):
    def __init__(
            self,
            scope  : Construct,
            id     : str,
            prefix : str,
            suffix : str,
            source : Path,
            liquid : str,
            bucket : aws_s3.Bucket = None,
            **kwargs
    ) -> None:

        super().__init__(scope, id, **kwargs)

        self.__prefix = prefix
        self.__suffix = suffix
        self.__source = source
        self.__liquid = liquid

        self.__bucket_name = f'{self.__prefix}-store-document-{self.__suffix}'

        self.__bucket = bucket or S3CustomBucketConstruct(
            scope                    = self,
            id                       = self.__bucket_name,
            bucket_name              = self.__bucket_name,
            recursive_object_removal = True,
            block_public_access      = aws_s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy           = RemovalPolicy.DESTROY,
            cors                     = [
                aws_s3.CorsRule(
                    allowed_methods=[
                        aws_s3.HttpMethods.GET
                    ],
                    allowed_origins=["*"],
                )
            ]
        )

        
        base_image_dockerfile =  "Dockerfile.base"
        base_image_path       = str(self.__source)
        base_image_tag        =  "lambdabase:latest"
        base_docker_image     = self.__build_docker_image(base_image_path, base_image_dockerfile, base_image_tag)

        self.__create_pipeline()

    def __build_docker_image(self, path, dockerfile, tag):
        """
        Build a Docker image from a Dockerfile.
        
        Args:
            path (str): Path to the directory containing the Dockerfile.
            tag (str): Tag to give to the built image.
        
        Returns:
            image: The built image object if successful.
        """
        print(f"Building Docker image '{tag}' from Dockerfile at '{path}'...")

        client = docker.from_env()

        try:
            # Build the image
            image, build_log = client.images.build(path=path, tag=tag, dockerfile=dockerfile, rm=True)
            
            # Optionally, print build logs
            for log in build_log:
                if 'stream' in log:
                    print(log['stream'].strip())
            
            print(f"Image built successfully: {image.tags}")
            return image
        except docker.errors.BuildError as e:
            print(f"Failed to build image: {e.msg}")
        except Exception as e:
            print(f"An error occurred: {e}")



    def __create_pipeline(self):

        table_name = f'{self.__prefix}-table-pipeline'
        table_pk   = 'DocumentID'
        table_sk   = 'OrderStamp'

        index_name = f'{self.__prefix}-index-progress'
        index_pk   = 'StageState'
        index_sk   = 'OrderStamp'
    
        self.__tdd_table_pipeline = aws_dynamodb.Table(
            scope           = self,
            id              = table_name,
            table_name      = table_name,
            partition_key   = aws_dynamodb.Attribute(name = table_pk, type = aws_dynamodb.AttributeType.STRING),
          # sort_key        = aws_dynamodb.Attribute(name = table_sk, type = aws_dynamodb.AttributeType.STRING), # do not want sk -> access item with just DocumentID
            removal_policy  = RemovalPolicy.DESTROY,
        )

        self.__tdd_table_pipeline.add_global_secondary_index(
            index_name      = index_name,
            partition_key   = aws_dynamodb.Attribute(name = index_pk, type = aws_dynamodb.AttributeType.STRING),
            sort_key        = aws_dynamodb.Attribute(name = index_sk, type = aws_dynamodb.AttributeType.STRING),
            projection_type = aws_dynamodb.ProjectionType.ALL,
        )

        self.__tdd_store_document = self.__bucket

        self.__common_variables = {
            'STORE_DOCUMENT' : self.__tdd_store_document.bucket_name,
            'TABLE_PIPELINE' : self.__tdd_table_pipeline.table_name,
            'INDEX_PROGRESS' : index_name,
            'PREFIX'         : self.__prefix,
            'SUFFIX'         : self.__suffix,
            'ACCOUNT'        : Aws.ACCOUNT_ID,
            'REGION'         : Aws.REGION,
        }

      # Constructs Pipeline Stage Process Lambdas
        pipeline_process_construct = PipelineProcessConstruct(
            scope  = self,
            id     = f'{self.__prefix}-pipeline-process',
            prefix = self.__prefix,
            common = self.__common_variables,
            source = self.__source,
            bucket = self.__tdd_store_document,
            liquid = self.__liquid
        )

      # Constructs Pipeline Progress Manager Lambdas
        pipeline_manager_construct = PipelineManagerConstruct(
            scope  = self,
            id     = f'{self.__prefix}-pipeline-manager',
            prefix = self.__prefix,
            source = self.__source,
            common = self.__common_variables
        )

      # Constructs Pipeline Startup Trigger Lambdas
        pipeline_trigger_construct = PipelineTriggerConstruct(
            scope  = self,
            id     = f'{self.__prefix}-pipeline-trigger',
            prefix = self.__prefix,
            source = self.__source,
            common = self.__common_variables,
            bucket = self.__bucket
        )

        self.__grant_persistence_permissions(
            pipeline_process_construct,
            pipeline_manager_construct,
            pipeline_trigger_construct
        )

      # Construct Pipeline State Machine
        pipeline_machine_construct = PipelineMachineConstruct(
            scope                      = self,
            id                         = f'{self.__prefix}-state-pipeline',
            prefix                     = self.__prefix,
            pipeline_process_construct = pipeline_process_construct,
            pipeline_manager_construct = pipeline_manager_construct,
            pipeline_trigger_construct = pipeline_trigger_construct
        )

        pipeline_trigger_construct.arm_s3_trigger()
      # pipeline_trigger_construct.arm_s3_trigger_delayed() # custom resource

    def __grant_persistence_permissions(self,
                                        pipeline_process_construct : PipelineProcessConstruct,
                                        pipeline_manager_construct : PipelineManagerConstruct,
                                        pipeline_trigger_construct : PipelineTriggerConstruct):

        for lambda_function in pipeline_manager_construct.get_manager_lambdas().values() :
            self.__tdd_table_pipeline.grant_read_write_data(lambda_function)

        for lambda_function in pipeline_process_construct.get_stage_await_lambdas().values() :
            self.__tdd_table_pipeline.grant_read_write_data(lambda_function)
            self.__tdd_store_document.grant_read_write(lambda_function)

        for lambda_function in pipeline_process_construct.get_stage_actor_lambdas().values() :
            self.__tdd_table_pipeline.grant_read_write_data(lambda_function)
            self.__tdd_store_document.grant_read_write(lambda_function)

        for lambda_function in pipeline_process_construct.get_stage_begin_lambdas().values() :
            self.__tdd_table_pipeline.grant_read_write_data(lambda_function)
            self.__tdd_store_document.grant_read_write(lambda_function)

        for lambda_function in pipeline_trigger_construct.get_trigger_lambdas().values() :
            self.__tdd_table_pipeline.grant_read_write_data(lambda_function)
