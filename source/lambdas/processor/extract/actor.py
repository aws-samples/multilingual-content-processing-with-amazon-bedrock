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


import base64
import json
import boto3


class ProcessImage():
    def generateJson(self, document: Document):
        try:

            document.CurrentMap.StageS3Uri = S3Uri(Bucket=STORE_BUCKET, Prefix=f'acquire/{document.DocumentID}')
            response = S3Client.get_object(Bucket=STORE_BUCKET, Key=f'acquire/{document.DocumentID}')
            
            session = boto3.Session()

            image_content = response['Body'].read()
            image_base64 = base64.b64encode(image_content)
            base64_string = image_base64.decode('utf-8')
        
            table_format_prompt = '''
            Here's a formalized prompt combining all the instructions:

            Objective:
            You are tasked with crafting a detailed and highly specific instruction set for a Language Model (LLM) that functions like an Optical Character Recognition (OCR) system. 
            åThe goal is to enable the model to accurately and comprehensively extract data from images.

            Guidelines for Writing the Prompt:

            1. Specify the Desired Data Points:
            Enumerate each category of data that needs to be extracted from the image, such as company names, comopany role in the context of the image for example supplier or buyer,  transaction dates, financial amounts, product or service descriptions, and any identifiers like invoice numbers.
            
            2. Detail the Structure and Format:
            Describe the common layout found on typical documents of this type. Include details about the presence of headers, tables, lists, or footnotes which might contain relevant information, guiding the model on where to focus within the document.
            
            3. Highlight Common Challenges and Solutions:
            Acknowledge potential OCR challenges such as text alignment, fonts, and character recognition errors. Provide guidelines on how to address these issues to improve data extraction accuracy.

            4. Define the Output Format:
            - Direct the model to structure the output in a JSON format, adhering to JSON Schema Draft 7 standards to ensure compatibility and ease of integration with downstream systems.
            - Do not use nested structures, flatten nested structures to facilitate easier data handling and analysis. For instance, convert { "contact": {"phone": "string", "email": "string"}} to {"contact_phone": "string", "contact_email": "string"}.
            
            Incorporate Examples:
            Include examples of both the input and the desired output. This will help the model better understand the task and the expected results.
            
            Use Descriptive Language:
            Use precise and descriptive language to eliminate ambiguity. Ensure that the instructions are thorough and detailed enough to guide the model without any additional human clarification.

            Example Prompt:
            `Please extract all textual and numerical data from the provided image of an invoice. Required data includes the issuer's details (name, address, contact), 
            each item's description, quantity, unit price, total item price, the invoice number, date of issue, and total amount due. 
            Organize each piece of data according to its appearance in the invoice, such as header information, table entries, and footer details. 
            Present the extracted data in a structured JSON format, ensuring each element is clearly categorized and formatted as outlined.`

            Output Instructions:
            Ensure the output strictly contains the generated prompt based on these instructions, with no additional text or commentary.

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
            response_body = response_body['content'][0]['text']
            print("prepared prompt", response_body)

            print('document.CurrentMap.StageS3Uri: ', document.CurrentMap.StageS3Uri.Url,)


            da = DocAnalysis(
                file_path=document.CurrentMap.StageS3Uri.Url,
                max_tokens=5000,
                temperature=0,
                boto3_session=session
            )
            
            resp = da.generate_schema(message=response_body)
            schema = resp['output']

            print("schema: ", schema)

            resp = da.run(
                message='''Extract all textual and numerical information from the provided document with maximum accuracy and comprehensiveness.
                        Output Instructions:
                            Use the schema provided. Please in your generated output include only generated json nothing else
                        
                        Example Output Format:
                        {'abc': 123, "bcd": [], cda: {}, dca: "abc"}
                        ''',
                output_schema=schema
            )
        
            response_body = resp['output']
    

        except (
            # handle bedrock or S3 error
        ) as e:

            return None

        return response_body


# class ProcessImage():


#     def generateJson(self, document: Document):
#         try:

#             document.CurrentMap.StageS3Uri = S3Uri(Bucket=STORE_BUCKET, Prefix=f'acquire/{document.DocumentID}.png')
#             response = S3Client.get_object(Bucket=STORE_BUCKET, Key=f'acquire/{document.DocumentID}.png')
#             image_content = response['Body'].read()
#             image_base64 = base64.b64encode(image_content)
#             base64_string = image_base64.decode('utf-8')

#             print("document: ", document)
        
#             table_format_prompt = '''
#             Here's a formalized prompt combining all the instructions:

#             You are given an {document.ClassifyMap.Prompt} in {document.ClassifyMap.Language} Your task is to extract this information from the image and structure it as a JSON format

    
#             Output Instructions:
#             Please in your generated output include only JSON object nothing else, do not start your output with the text like 'Here is the JSON object with the extracted information from the invoice image, structured as per the provided guidelines:'
#             '''
            
#             payload = {
#                 "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
#                 "contentType": "application/json",
#                 "accept": "application/json",
#                 "body": {
#                     "anthropic_version": "bedrock-2023-05-31",
#                     "temperature": 0,
#                     "max_tokens": 5000,
#                     "messages": [
#                         {
#                             "role": "user",
#                             "content": [
#                                 {
#                                     "type": "image",
#                                     "source": {
#                                         "type": "base64",
#                                         "media_type": "image/png",
#                                         "data": base64_string
#                                     }
#                                 },
#                                 {
#                                     "type": "text",
#                                     "text": table_format_prompt
#                                 }
#                             ]
#                         }
#                     ]
#                 }
#             }

            
#             body_bytes = json.dumps(payload['body']).encode('utf-8')


#             response = BedrockClient.invoke_model(
#                 body=body_bytes,
#                 contentType=payload['contentType'],
#                 accept=payload['accept'],
#                 modelId=payload['modelId']
#             )
            
#             response_body = json.loads(response['body'].read().decode('utf-8'))
#             print(response_body)
#             response_body = response_body['content'][0]['text']

#         except (
#             # handle bedrock or S3 error
#         ) as e:

#             return None

#         return response_body

def lambda_handler(event, context):

    document = Document.from_dict(event)
    message  = Message(DocumentID = document.DocumentID)


    result = ProcessImage().generateJson(document)


    Logger.info(f'{STAGE} Actor : Started Processing DocumentID = {document.DocumentID}')

    key = f'{document.DocumentID.split('.')[0]}.json'
    print('s3 key: ', key)
    print('result: ', result)

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
