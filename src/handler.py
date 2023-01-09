import os

import boto3
from aws_lambda_context import LambdaContext
from aws_lambda_powertools import Logger
from botocore.config import Config
from botocore.exceptions import ClientError
from github import Github


config = Config(retries={"max_attempts": 60, "mode": "standard"})
ssm_client = boto3.client("ssm", config=config)
pipeline_client = boto3.client("codepipeline", config=config)

logger = Logger(
    service="aws-lambda-telemetry-eventbridge-enrichment",
    level=os.environ.get("LOG_LEVEL", "DEBUG"),
)


def get_ssm_parameter(ssm_parameter: str) -> str:
    try:
        parameter = ssm_client.get_parameter(Name=ssm_parameter, WithDecryption=True)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            raise KeyError(
                "Critical, required parameter was not found in SSM parameter store."
            )
        else:
            raise e

    return parameter["Parameter"]["Value"]


def get_pipeline_commit_sha(name: str, execution_id: str):
    try:
        parameter = pipeline_client.get_pipeline_execution(
            pipelineName=name, pipelineExecutionId=execution_id
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            raise KeyError("Critical, required pipeline was not found.")
        else:
            raise e

    return parameter["pipelineExecution"]["artifactRevisions"][0]["revisionId"]


def enrich_codepipeline_event(event: dict, context: LambdaContext) -> str:
    try:
        logger.info(f"Lambda Request ID: {context.aws_request_id}")
    except AttributeError:
        logger.info("No context object available")

    logger.debug(f'Event received from CodePipeline: "{event}"')

    # get github client credentials
    github_user = get_ssm_parameter("telemetry_github_user")
    github_token = get_ssm_parameter("telemetry_github_token")
    logger.debug(f"user {github_user}, token {github_token}")

    # get execution id from invocation
    execution_id = event["execution_id"]

    # get GitHub commit sha from execution id
    commit_sha = get_pipeline_commit_sha("telemetry-terraform-pipeline", execution_id)
    logger.debug(commit_sha)

    # get commit author(s) from sha
    g = Github(github_token)
    repo = g.get_repo("hmrc/telemetry-terraform")
    commit = repo.get_commit(sha=commit_sha)
    logger.debug(commit.commit.author.email)
    # translate git email -> slack id (simple lookup)

    return "hello world"


if __name__ == "__main__":
    lambda_context = LambdaContext()
    lambda_context.function_name = "enrich_codepipeline_event"
    lambda_context.aws_request_id = "abc-123"
    test_event = {"execution_id": "0d18ecc5-2611-436b-9d2f-ba7e9bfc721d"}
    enrich_codepipeline_event(event=test_event, context=lambda_context)
