# Use the official AWS Lambda Python runtime as base image
FROM public.ecr.aws/lambda/python:3.11

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.lambda_handler" ]

# Health check for local testing
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/2015-03-31/functions/function/invocations \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"requestContext":{"http":{"method":"GET","path":"/health"}}}' || exit 1
