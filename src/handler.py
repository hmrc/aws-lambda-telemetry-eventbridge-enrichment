import os

import boto3
from aws_lambda_context import LambdaContext
from aws_lambda_powertools import Logger
from botocore.config import Config
from botocore.exceptions import ClientError
from exceptions import EmptyEventDetailException
from exceptions import NoExecutionIdFoundException
from github import Github
from helper import Helper

config = Config(retries={"max_attempts": 60, "mode": "standard"})
ssm_client = boto3.client("ssm", config=config, region_name="eu-west-2")
pipeline_client = boto3.client("codepipeline", config=config, region_name="eu-west-2")

github_repo = "hmrc/telemetry-terraform"
github_token_param = "telemetry_github_token"

logger = Logger(
    service="aws-lambda-telemetry-eventbridge-enrichment",
    level=os.environ.get("LOG_LEVEL", "DEBUG"),
)
helper = Helper(logger)


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

    # Get the first artifact revision which is the source_output - don't assume there will always be one
    source_revision_list = [
        revision
        for revision in response["pipelineExecution"]["artifactRevisions"]
        if revision["name"] == "source_output"
    ]

    # Default revision identifier to empty string, only populate if the artifactRevisions has a 'source_output'
    # The 'source_output' is the standard name given to all our GitHub Source pipeline steps
    revision_id = ""

    if len(source_revision_list) > 0:
        revision_id = source_revision_list[0]["revisionId"]

    return revision_id


def get_github_author_email(github_token: str, commit_sha: str) -> str:
    if not commit_sha:
        author_email = "<not found - empty sha>"
    else:
        g = Github(github_token)
        repo = g.get_repo(github_repo)
        commit = repo.get_commit(sha=commit_sha)
        author_email = commit.commit.author.email

    return author_email


def get_github_commit_message_summary(github_token: str, commit_sha: str) -> str:
    if not commit_sha:
        commit_message_summary = "<not found - empty sha>"
    else:
        g = Github(github_token)
        repo = g.get_repo(github_repo)
        commit = repo.get_commit(sha=commit_sha)
        commit_message_summary = commit.commit.message.partition("\n")[0]

    return commit_message_summary


def enrich_sqs_event(sqs_message: list, context: LambdaContext) -> str:
    """
    Receives an sqs message that contains a CodePipeline event and enriches it.
    Wraps enrich_codepipeline_event.
    """
    try:
        logger.info(f"Lambda Request ID: {context.aws_request_id}")
    except AttributeError:
        logger.info("No context object available")

    logger.debug(f'Event received from SQS: "{sqs_message}"')

    event = helper.open_sqs_envelope(sqs_message)
    return enrich_codepipeline_event(event, context)


def enrich_codepipeline_event(event: dict, context: LambdaContext) -> str:
    """
    Enriches a CodePipeline event with:
    1. Execution ID
    2. Slack user of the person making the commit
    """
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
    logger.debug(f"commit_sha: {commit_sha}")

    # get commit author(s) from sha
    author_email = get_github_author_email(github_token, commit_sha)

    # translate git email -> slack id (simple lookup)
    slack_handle = helper.get_slack_handle(author_email)
    event.get("detail")["slack_handle"] = slack_handle
    commit_message_summary = get_github_commit_message_summary(github_token, commit_sha)
    event.get("detail")["commit_message_summary"] = commit_message_summary

    event.get("detail")[
        "enriched_title"
    ] = f"CodePipeline failed: {pipeline}. Committer: @{slack_handle} Sha: {commit_sha[:8]} - {commit_message_summary}"

    logger.debug(f'Final enriched event: "{event}"')

    return event
