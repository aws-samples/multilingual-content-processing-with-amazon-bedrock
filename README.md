# multilingual-content-processing-with-amazon-bedrock



### Architecture

![Architecture Diagram](/docs/architecture.png)

1. Documents are initially stored in an S3 bucket. These files trigger the AWS Trigger Lambda when uploaded to `s3://store-document-<account-number>/acquire/`. The Trigger Lambda function stores metadata about each document and tracks document processing states in the `mcp-table-pipeline` DynamoDB table. Initially, documents are stored with the stage `extrac` and state `waiting`, and the `state-pipeline` Step Function is triggered if it is not already running.

2. The Trigger Lambda plays a crucial role in storing metadata and managing the state of the document. The metadata is tracked using DynamoDB in the mcp-table-pipeline table, which records each document's progress through different stages of the pipeline. The Step Function orchestrates the workflow, and each document’s state is updated as it moves through the pipeline.

3. The **AWS Step Function** orchestrates the entire multi-stage document processing workflow, which includes stages such as **extraction**, **operation**, **reshaping**, **human augmentation**, and **cataloging**. Each stage is implemented using a serverless and stateless **Actor Model**, which allows each document to be processed independently. By leveraging the Step Function's **parallel state capability**, multiple documents are processed simultaneously, ensuring efficient and scalable execution.  

   - **Promote Manager Lambda**: This Lambda function manages the transition between stages. It queries DynamoDB to identify documents that have successfully completed the current stage and updates their state to `waiting` for the next stage.

4. Each stage of the pipeline follows the **Actor Model pattern** using **AWS Lambda functions** and **Amazon SQS**. The three key components in each stage are:

   - **Begin Lambda**: This Lambda retrieves all documents in the `waiting` state for the current stage from DynamoDB. It asynchronously invokes the **Actor Lambda** for each document and updates the document’s state to `running` in DynamoDB, indicating that processing has started.
   
   - **Actor Lambda**: This Lambda contains the **business logic** for each stage. After completing the processing, it sends a message to an **Amazon SQS** queue, signaling that the document has been processed. This message includes metadata such as the document ID and the result of the processing.

   - **Await Lambda**: The Await Lambda is triggered by the SQS message. It reads the message, retrieves the corresponding document from DynamoDB, and updates the document’s state to `success` if the Actor Lambda completed successfully. If necessary, this Lambda could also handle error states.

    **Benefits of This Pattern**:  
   - **Decoupling of Stages**: Each stage of the workflow is isolated, with distinct Lambdas handling specific tasks and SQS managing the messaging and state transition between stages.
   - **Scalability**: Lambdas (Begin, Actor, and Await) are stateless and independent, allowing the system to scale horizontally with the number of documents processed.
   - **Resilience**: DynamoDB tracks each document’s state, allowing the system to gracefully handle failures. If a Lambda fails, the document state is clear, enabling retry mechanisms or error handling.
   - **Parallel Execution**: Using asynchronous invocations and SQS, the architecture supports parallel processing of multiple documents across different stages.

5. **Stage 1: Extract**  
   In the **Extract** stage, the workflow downloads the JSON schema from `s3://store-document-<account-number>/schema/invoice_schema.json` and embeds it into a prompt. A multimodal extraction process is executed on the document using **Amazon Bedrock**, facilitated by the lightweight AWS framework [**Rhubarb**](https://github.com/awslabs/rhubarb). This process is responsible for extracting structured data from the document (e.g., PDFs) based on the schema.

6. **Stage 2: Operate**  
   The **Operate** stage involves performing **data transformations** on the output from the extraction stage. This step include tasks such as **JSON flattening** or applying custom business logic to the extracted data.

7. **Stage 3: Reshape**  
   In the **Reshape** stage, the output from the **Operate** step is transformed again to match the **Amazon Textract** output format. This reshaped data is necessary for human validation templates used in the next stage (Amazon A2I).

8. **Stage 4: Augment (Human Review)**  
   The **Augment** stage submits the reshaped data for **human review** using **Amazon A2I (Augmented AI)**. Once a human reviewer completes the task, an **Amazon EventBridge** event is generated, and the review completion message is sent to an **SQS queue**. The **Await Lambda** reads this message to update the document’s state in DynamoDB.

9. **Stage 5: Catalog**  
   The final stage is the **Catalog** step, where the processed and validated documents are constructed and stored in an appropriate format, such as Excel. The final document is then written back to an S3 bucket for long-term storage or further downstream processing.




### Basic Usage Workflow:
* Put a scanned image  in s3 at `s3://store-document-<account-number>/acquire/`
* This action triggers the `state-pipeline` step function which will: 
  * Detect the langauage, schema and type of the document in the image with Amazon Bedrock Claude Sonnet
  * Extract the data from the image in the json format
  * Apply business rules to the extracted JSON (currently a pass-through operation)
  * Convert the extracted JSON to Textract format 
  * Send the image and extracted content to A2I for human review
  * Once human review is complete, convert output to a spreadsheet 
* Monitor document status in DynamoDB in the `table-pipeline` table
* Once your document has reached the `Status` `Augment#Waiting`, it's time to perform human review using the worker portal (descrbied below)
* After human review, find the final Excel spreadsheet in `s3://store-resource-<account-number>/acquire/catalog`


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

3. Authenticate Docker to an Amazon Elastic Container Registry (ECR) Public repository:
- aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aw

*Instruction to Deploy Application to AWS Cloud*

1. cd multilingual-content-processing
3. python3 -m venv .venv                    - Create virtual environment
3. source .venv/bin/activate                - Enter virtual environment
4. pip install -r requirements.txt          - Install dependencies in virtual environment
5. cdk bootstrap                            - Only run this once per account setup
6. edit cdk.json, set your work team name   - Pre-create the workteam via aws console, and make sure to match workteam name in same region/account
7. cdk deploy --all                         - Deploy application

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.