import json
import os
from urllib.parse import parse_qs
from urllib.parse import urlparse

import boto3
from aws_lambda_context import LambdaContext
from aws_lambda_powertools import Logger
from botocore.config import Config
from botocore.exceptions import ClientError
from exceptions import EmptyEventDetailException
from exceptions import NoExecutionIdFoundException
from github import Auth
from github import Github
from helper import Helper

config = Config(retries={"max_attempts": 60, "mode": "standard"})
ssm_client = boto3.client("ssm", config=config, region_name="eu-west-2")
pipeline_client = boto3.client("codepipeline", config=config, region_name="eu-west-2")

github_token_param = "/secrets/github/telemetry_github_token"

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


def get_pipeline_commit_data(name: str, execution_id: str) -> dict:
    """
    Returns map like:
    {
        "name": "source_output",
        "revisionId": "afd432bc775c1a24c17b421187950a3af15db703",
        "revisionSummary": "lambda-eventbridge-enrichment0.0.12->0.0.15 (#2250)",
        "revisionUrl": "https://github.com/hmrc/telemetry-terraform/commit/afd432bc775c1a24c17b421187950a3af15db703"
    }
    """
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
    if len(source_revision_list) > 0:
        return source_revision_list[0]
    else:
        # return empty dictionary
        return {}


def get_github_repo_from_revision_url(revision_url: str) -> str:
    revision_url_details = urlparse(revision_url)
    return parse_qs(revision_url_details.query)["FullRepositoryId"][0]


def get_github_author_email(
    github_token: str, github_repo: str, commit_sha: str
) -> str:
    if not commit_sha:
        author_email = "<not found - empty sha>"
    else:
        g = Github(auth=Auth.Token(github_token))
        repo = g.get_repo(github_repo)
        commit = repo.get_commit(sha=commit_sha)
        author_email = commit.commit.author.email

    return author_email


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

    event["message-header"] = f"CodePipeline failed: {pipeline}"

    # get github client credentials
    github_token = get_ssm_parameter(github_token_param)

    # get GitHub commit details from execution id
    commit_data = get_pipeline_commit_data(pipeline, execution_id)
    if len(commit_data.keys()) == 0:
        # did not get any github commit details so just return event as is
        return event

    commit_sha = commit_data["revisionId"]
    logger.debug(f"commit_sha: {commit_sha}")

    # get GitHub repo name from revision URL
    github_repo = get_github_repo_from_revision_url(commit_data["revisionUrl"])

    # get commit author(s) from sha
    author_email = get_github_author_email(
        github_token=github_token,
        github_repo=github_repo,
        commit_sha=commit_sha,
    )

    # translate git email -> slack id (simple lookup)
    slack_handle = helper.get_slack_handle(author_email)
    commit_url = f"https://github.com/{github_repo}/commit/{commit_sha}"
    revision_summary = json.loads(commit_data["revisionSummary"])
    commit_message_summary = revision_summary["CommitMessage"].partition("\n")[0]
    pipeline_url = f"https://eu-west-2.console.aws.amazon.com/codesuite/codepipeline/pipelines/{pipeline}/view"

    event["message-content"] = {
        "mrkdwn_in": ["text"],
        "color": "danger",
        "text": f"Build of <{pipeline_url}|{pipeline}> failed after a commit by <@{slack_handle}> - <{commit_url}|{commit_message_summary}>",
    }
    logger.debug(f'Final enriched event: "{event}"')

    return event
