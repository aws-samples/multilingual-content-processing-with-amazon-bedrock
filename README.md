# multilingual-content-processing



### Architecture

![Architecture Diagram](/docs/architecture.png)

### Basic Usage Workflow:
* Put a scanned image  in s3 at `s3://store-resource-<account-number>-<region>/acquire/`
* This action triggers the `state-pipeline` step function which will: 
  * Detect the langauage, schema and type of the document in the image with Amazon Bedrock Claude Sonnet
  * Extract the data from the image in the json format
  * Apply business rules to the extracted JSON (currently a pass-through operation)
  * Convert the extracted JSON to Textract format 
  * Send the image and extracted content to A2I for human review
  * Once human review is complete, convert output to a spreadsheet 
* Monitor document status in DynamoDB in the `table-pipeline` table
* Once your document has reached the `Status` `Augment#Waiting`, it's time to perform human review using the worker portal (descrbied below)
* After human review, find the final Excel spreadsheet in `s3://store-resource-<account-number>-<region>/acquire/catalog`


## Installation
### SageMaker Private Workforce Setup

This application uses SageMaker labeling workforces to manage workers and distribute tasks. Create a private workforce, workers team called `primary` and `quality`, and assign yourself to both teams using these instructions: https://docs.aws.amazon.com/sagemaker/latest/dg/sms-workforce-create-private-console.html#create-workforce-sm-console

Once you’ve added yourself to the private workforce teams and confirmed your email, take note of the worker portal URL from the AWS Console by:

* Navigate to SageMaker
* Navigate to Ground Truth → Labeling workforces
* Click the Private tab
* Note the URL `Labeling portal sign-in` - you will log in here to perform A2I human reviews.

### Application Deployment with CDK

*Pre-Requisites*

1. Install CDK Toolkit

- npm install -g aws-cdk

2. Install Docker, and Run

- For Mac : https://docs.docker.com/docker-for-mac/install
- For Win : https://docs.docker.com/docker-for-windows/install

*Instruction to Deploy Application to AWS Cloud*

1. cd multilingual-content-processing
3. python3 -m venv .venv                    - Create virtual environment
3. source .venv/bin/activate                - Enter virtual environment
4. pip install -r requirements.txt          - Install dependencies in virtual environment
5. cdk bootstrap                            - Only run this once per account setup
6. edit cdk.json, set your work team name   - Pre-create the workteam via aws console, and make sure to match workteam name in same region/account
7. cdk deploy --all                         - Deploy application

