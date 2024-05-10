# Use a locally available image as the base image
FROM lambdabase:latest

# Define build-time variables
ARG STAGE
ARG ASPECT

# Set the working directory inside the container
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the specific handler file
COPY /processor/${STAGE}/${ASPECT}.py ${LAMBDA_TASK_ROOT}/handler.py

# Optionally copy utils.py if it exists in the specified processor stage directory
COPY /processor/catalog/utils.py ${LAMBDA_TASK_ROOT}/utils.py

# Set the command to launch the Lambda handler
CMD ["handler.lambda_handler"]
