# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from shared.defines import *
from shared.environ import *
from shared.helpers import *


from shared.message  import Message
from shared.document import Document
from shared.database import Database
from shared.message  import Message
from shared.store    import Store
from shared.bus      import Bus
from shared.storage  import S3Uri
from shared.loggers import Logger
from shared.clients import BedrockClient, S3Client
from rhubarb import DocAnalysis


import json
import boto3


class ProcessImage():
    def generateJson(self, document: Document):
        try:

            document.CurrentMap.StageS3Uri = S3Uri(Bucket=STORE_BUCKET, Prefix=f'acquire/{document.DocumentID}')            
            session = boto3.Session()

            response = S3Client.get_object(Bucket=STORE_BUCKET, Key=f'schema/invoice_schema.json')
            schema_content =  response['Body'].read().decode('utf-8')
            schema = json.loads(schema_content)


            da = DocAnalysis(
                file_path=document.CurrentMap.StageS3Uri.Url,
                max_tokens=5000,
                temperature=0,
                boto3_session=session
            )
            

            resp = da.run(
                message='''Extract all textual and numerical information from the provided document with maximum accuracy and comprehensiveness.
                        Output Instructions:
                            Use the schema provided. Please in your generated output include only generated json nothing else
                        
                        Example Output Format:
                        {'abc': 123, "bcd": [], cda: {}, dca: "abc"}
                        ''',
                output_schema= schema
            )
        
            response_body = resp['output']
    

        except (
            # handle bedrock or S3 error
        ) as e:

            return None

        return response_body



def lambda_handler(event, context):

    document = Document.from_dict(event)
    message  = Message(DocumentID = document.DocumentID)


    result = ProcessImage().generateJson(document)


    Logger.info(f'{STAGE} Actor : Started Processing DocumentID = {document.DocumentID}')

    key = f'{document.DocumentID.split('.')[0]}.json'


    json_string = json.dumps(result)

    Store.PutFile(STAGE, key, json_string.encode('utf-8'))

    message.MapUpdates.StageS3Uri = S3Uri(Bucket = STORE_BUCKET, Prefix = f'{STAGE}/{document.DocumentID}')

    message.FinalStamp = GetCurrentStamp()

    print(message)

    Bus.PutMessage(stage = STAGE, message_body = message.to_json())

    Logger.info(f'{STAGE} Actor : Stopped Processing DocumentID = {document.DocumentID}')

    return PASS

if  __name__ == '__main__':

	Bus.Purge(stage = STAGE)

	lambda_handler(Document(DocumentID = '001', AcquireMap = dict(InputS3Url = 'acquire/1/001.pdf')).to_dict(), None)
