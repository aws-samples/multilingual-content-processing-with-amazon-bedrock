# Syntax to use a locally available image as the base image
FROM lambdabase:latest

ARG STAGE

COPY /trigger/${STAGE}/*.py  ${LAMBDA_TASK_ROOT}

WORKDIR ${LAMBDA_TASK_ROOT}

# Set the command to launch the Lambda handler
CMD ["handler.lambda_handler"]
