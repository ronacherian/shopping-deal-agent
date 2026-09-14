FROM public.ecr.aws/lambda/python:3.12

# Install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application source code
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Set the Lambda handler
CMD [ "src.main.lambda_handler" ]
