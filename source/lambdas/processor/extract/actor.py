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


import base64
import json



class ProcessImage():


    def generateJson(self, document: Document):
        try:

            document.CurrentMap.StageS3Uri = S3Uri(Bucket=STORE_BUCKET, Prefix=f'acquire/{document.DocumentID}.png')
            response = S3Client.get_object(Bucket=STORE_BUCKET, Key=f'acquire/{document.DocumentID}.png')
            image_content = response['Body'].read()
            image_base64 = base64.b64encode(image_content)
            base64_string = image_base64.decode('utf-8')

            print("document: ", document)
        
            table_format_prompt = '''
            Here's a formalized prompt combining all the instructions:

            You are given an {document.ClassifyMap.Prompt} in {document.ClassifyMap.Language}Your task is to extract this information from the image and structure it as a JSON format

    
            Output Instructions:
            Please in your generated output include only JSON object nothing else, do not start your output with the text like 'Here is the JSON object with the extracted information from the invoice image, structured as per the provided guidelines:'
            '''
            
            payload = {
                "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
                "contentType": "application/json",
                "accept": "application/json",
                "body": {
                    "anthropic_version": "bedrock-2023-05-31",
                    "temperature": 0,
                    "max_tokens": 5000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": base64_string
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": table_format_prompt
                                }
                            ]
                        }
                    ]
                }
            }

            
            body_bytes = json.dumps(payload['body']).encode('utf-8')


            response = BedrockClient.invoke_model(
                body=body_bytes,
                contentType=payload['contentType'],
                accept=payload['accept'],
                modelId=payload['modelId']
            )
            
            response_body = json.loads(response['body'].read().decode('utf-8'))
            print(response_body)
            response_body = response_body['content'][0]['text']

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

    key = f'{document.DocumentID}.json'
    Store.PutFile(STAGE, key, result.encode('utf-8'))

    message.MapUpdates.StageS3Uri = S3Uri(Bucket = STORE_BUCKET, Prefix = f'{STAGE}/{document.DocumentID}')

    message.FinalStamp = GetCurrentStamp()

    print(message)

    Bus.PutMessage(stage = STAGE, message_body = message.to_json())

    Logger.info(f'{STAGE} Actor : Stopped Processing DocumentID = {document.DocumentID}')

    return PASS

if  __name__ == '__main__':

	Bus.Purge(stage = STAGE)

	lambda_handler(Document(DocumentID = '001', AcquireMap = dict(InputS3Url = 'acquire/1/001.pdf')).to_dict(), None)
