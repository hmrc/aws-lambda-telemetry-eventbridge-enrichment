import os

import boto3
from aws_lambda_context import LambdaContext
from aws_lambda_powertools import Logger
from botocore.config import Config
from botocore.exceptions import ClientError
from github import Github

from .exceptions import EmptyEventDetailException
from .exceptions import NoExecutionIdFoundException
from .helper import Helper


config = Config(retries={"max_attempts": 60, "mode": "standard"})
ssm_client = boto3.client("ssm", config=config, region_name="eu-west-2")
pipeline_client = boto3.client("codepipeline", config=config, region_name="eu-west-2")

github_repo = "hmrc/telemetry-terraform"
github_token_param = "telemetry_github_token"

logger = Logger(
    service="aws-lambda-telemetry-eventbridge-enrichment",
    level=os.environ.get("LOG_LEVEL", "DEBUG"),
)


def get_ssm_parameter(ssm_parameter: str) -> str:
    try:
        parameter = ssm_client.get_parameter(Name=ssm_parameter, WithDecryption=True)
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
        raise e

    return parameter["Parameter"]["Value"]


def get_pipeline_commit_sha(name: str, execution_id: str) -> str:
    try:
        response = pipeline_client.get_pipeline_execution(
            pipelineName=name, pipelineExecutionId=execution_id
        )
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
        raise e

    # Get the first artifact revision which is the source_output
    source_revision = [
        revision
        for revision in response["pipelineExecution"]["artifactRevisions"]
        if revision["name"] == "source_output"
    ][0]

    return source_revision["revisionId"]


def get_github_author_email(github_token: str, commit_sha: str) -> str:
    g = Github(github_token)
    repo = g.get_repo(github_repo)
    commit = repo.get_commit(sha=commit_sha)
    return commit.commit.author.email


def enrich_codepipeline_event(event: dict, context: LambdaContext) -> str:
    try:
        logger.info(f"Lambda Request ID: {context.aws_request_id}")
    except AttributeError:
        logger.info("No context object available")

    logger.debug(f'Event received from CodePipeline: "{event}"')

    if not event.get("detail"):
        logger.error("No detail found in event, cannot continue")
        raise EmptyEventDetailException

    if event.get("detail").get("execution-id") is None:
        logger.error("No execution id found in detail, cannot continue")
        raise NoExecutionIdFoundException

    detail = event.get("detail")
    pipeline = detail.get("pipeline")
    execution_id = detail.get("execution-id")

    # get github client credentials
    github_token = get_ssm_parameter(github_token_param)

    # get GitHub commit sha from execution id
    commit_sha = get_pipeline_commit_sha(pipeline, execution_id)
    logger.debug(commit_sha)

    # get commit author(s) from sha
    author_email = get_github_author_email(github_token, commit_sha)

    # translate git email -> slack id (simple lookup)
    helper = Helper(logger)
    slack_handle = helper.get_slack_handle(author_email)
    event.get("detail")["slack_handle"] = slack_handle

    return event
