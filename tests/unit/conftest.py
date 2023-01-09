import os
from datetime import datetime
from datetime import timedelta

import boto3
import pytest
import pytz
from aws_lambda_context import LambdaContext
from botocore.stub import Stubber
from moto import mock_ssm

region = "eu-west-2"


@pytest.fixture(autouse=True)
def initialise_environment_variables():
    os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture(scope="function")
def lambda_event():
    return {}


@pytest.fixture(scope="function")
def context():
    lambda_context = LambdaContext()
    lambda_context.function_name = "lambda_handler"
    lambda_context.aws_request_id = "abc-123"
    return lambda_context


@pytest.fixture()
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = region
    os.environ["AWS_DEFAULT_REGION"] = region


@pytest.fixture(scope="function")
def ssm(aws_credentials):
    with mock_ssm():
        conn = boto3.client("ssm", region_name="eu-west-2")
        yield conn


@pytest.fixture(scope="function")
def codepipeline_client_stub():
    from src.handler import pipeline_client

    with Stubber(pipeline_client) as stubber:
        stubber.activate()
        yield stubber
        stubber.deactivate()
        stubber.assert_no_pending_responses()


@pytest.fixture(scope="function")
def get_pipeline_execution_success_fixture():
    return {
        "pipelineExecution": {
            "pipelineName": "telemetry-terraform-pipeline",
            "pipelineVersion": 13,
            "pipelineExecutionId": "0d18ecc5-2611-436b-9d2f-ba7e9bfc721d",
            "status": "Succeeded",
            "artifactRevisions": [
                {
                    "name": "source_output",
                    "created": datetime.now(pytz.utc) - timedelta(minutes=61),
                    "revisionId": "bc051f8d7fbf183dbb840462cb5c17d887964842",
                    "revisionSummary": "TEL-3481 create pagerduty-config-deployer",
                    "revisionUrl": "https://github.com/hmrc/telemetry-terraform/commit/bc051f8d7fbf183dbb840462cb5c17d887964842",
                }
            ],
        },
        "ResponseMetadata": {
            "RequestId": "bdb16569-7833-4468-96ba-588de0ae9c06",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "bdb16569-7833-4468-96ba-588de0ae9c06",
                "date": "Tue, 10 Jan 2023 11:34:48 GMT",
                "content-type": "application/x-amz-json-1.1",
                "content-length": "2066",
            },
            "RetryAttempts": 0,
        },
    }


@pytest.fixture(scope="function")
def cloudwatch_event_pipeline_failed():
    return {
        "version": "0",
        "id": "CWE-event-id",
        "detail-type": "CodePipeline Pipeline Execution State Change",
        "source": "aws.codepipeline",
        "account": "123456789012",
        "time": "2017-04-22T03:31:47Z",
        "region": "eu-west-2",
        "resources": [
            "arn:aws:codepipeline:eu-west-2:123456789012:pipeline:myPipeline"
        ],
        "detail": {
            "pipeline": "myPipeline",
            "version": "1",
            "state": "FAILED",
            "execution-id": "01234567-0123-0123-0123-012345678901",
        },
    }


@pytest.fixture(scope="function")
def cloudwatch_event_invalid_no_detail():
    return {
        "id": "cdc73f9d-aea9-11e3-9d5a-835b769c0d9c",
        "detail-type": "Scheduled Event",
        "source": "aws.codepipeline",
        "account": "123456789012",
        "time": "2017-04-22T03:31:47Z",
        "region": "eu-west-2",
        "resources": [
            "arn:aws:codepipeline:eu-west-2:123456789012:pipeline:myPipeline"
        ],
        "detail": {},
    }


@pytest.fixture(scope="function")
def cloudwatch_event_invalid_no_execution_id():
    return {
        "version": "0",
        "id": "CWE-event-id",
        "detail-type": "CodePipeline Pipeline Execution State Change",
        "source": "aws.codepipeline",
        "account": "123456789012",
        "time": "2017-04-22T03:31:47Z",
        "region": "eu-west-2",
        "resources": [
            "arn:aws:codepipeline:eu-west-2:123456789012:pipeline:myPipeline"
        ],
        "detail": {
            "pipeline": "myPipeline",
            "version": "1",
            "state": "FAILED",
        },
    }
