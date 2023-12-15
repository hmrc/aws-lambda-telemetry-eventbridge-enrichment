import os

import pytest
from aws_lambda_powertools import Logger
from helper import Helper


@pytest.fixture
def valid_users():
    return [
        ["gavD@users.noreply.github.com", "gavin.davies1"],
        ["1422984+webit4me@users.noreply.github.com", "ali.bahman"],
    ]


@pytest.fixture
def helper():
    logger = Logger(
        service="aws-lambda-telemetry-eventbridge-enrichment",
        level=os.environ.get("LOG_LEVEL", "DEBUG"),
    )
    return Helper(logger)


def test_get_slack_handle_for_valid_users(valid_users, helper):
    """Test that users that are in the helper are returned correctly"""
    for user in valid_users:
        assert helper.get_slack_handle(user[0]) == user[1]


def test_get_slack_handle_for_invalid_user_throws(helper):
    """Test that users that are not in the helper causes an exception to be raised"""
    helper.get_slack_handle("i-do-not-exist")


def test_open_sqs_envelope(
    helper, sqs_message_containing_cloudwatch_event_pipeline_failed
):
    """Test that the SQS envelope can be opened"""
    event = helper.open_sqs_envelope(
        sqs_message_containing_cloudwatch_event_pipeline_failed
    )
    assert event.get("id") == "4da4f3e3-5b27-557c-b293-a8a8b4a54213"
