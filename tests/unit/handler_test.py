from unittest import mock
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from github import Github


def test_get_ssm_parameter(ssm):
    """Test that retrieving an SSM parameter that does exist returns the parameter"""
    # Arrange & Act
    from handler import get_ssm_parameter

    ssm.put_parameter(Name="telemetry_github_user", Value="foobar")
    parameter_result = get_ssm_parameter("telemetry_github_user")

    # Assert
    assert parameter_result == "foobar"


def test_get_ssm_parameter_raises_error(ssm):
    """Test that retrieving an SSM parameter that does not exist raises an error"""
    # Arrange & Act
    from handler import get_ssm_parameter

    with pytest.raises(ClientError):
        parameter_result = get_ssm_parameter("telemetry_github_user")

        # Assert
        assert parameter_result is None


def test_get_pipeline_commit_data_returns_commit_from_source_output(
    codepipeline_client_stub, get_pipeline_execution_success_fixture
):
    # Arrange
    from handler import get_pipeline_commit_data

    codepipeline_client_stub.add_response(
        "get_pipeline_execution", get_pipeline_execution_success_fixture
    )

    # Act
    git_data = get_pipeline_commit_data(
        "telemetry-terraform-pipeline", "0d18ecc5-2611-436b-9d2f-ba7e9bfc721d"
    )

    # Assert
    assert git_data == {
        "name": "source_output",
        "revisionId": "bc051f8d7fbf183dbb840462cb5c17d887964842",
        "revisionSummary": "TEL-3481 create pagerduty-config-deployer",
        "revisionUrl": "https://github.com/hmrc/telemetry-terraform/commit/bc051f8d7fbf183dbb840462cb5c17d887964842",
    }


def test_get_pipeline_commit_data_returns_empty_with_no_source_output(
    codepipeline_client_stub, get_pipeline_execution_failure_fixture
):
    # Arrange
    from handler import get_pipeline_commit_data

    codepipeline_client_stub.add_response(
        "get_pipeline_execution", get_pipeline_execution_failure_fixture
    )

    # Act
    git_data = get_pipeline_commit_data(
        "telemetry-terraform-pipeline", "0d18ecc5-2611-436b-9d2f-ba7e9bfc721d"
    )

    # Assert
    assert git_data == {
        "name": "",
        "revisionId": "",
        "revisionSummary": "",
        "revisionUrl": "",
    }


@patch.object(Github, "get_repo")
def test_get_github_author_returns_valid(
    mock_get_repo, codepipeline_client_stub, get_pipeline_execution_failure_fixture
):
    # Arrange
    from handler import get_github_author_email

    author = mock.Mock()
    author.email = "mock@example.com"
    commit = mock.Mock()
    commit.author = author
    mock_commit = mock.Mock()
    mock_commit.commit = commit
    mock_get_repo.return_value.get_commit.return_value = mock_commit

    # Act
    author_email = get_github_author_email("mock_token", "mock_sha")

    # Assert
    assert author_email == "mock@example.com"


def test_get_github_author_returns_not_found(
    codepipeline_client_stub, get_pipeline_execution_failure_fixture
):
    # Arrange
    from handler import get_github_author_email

    # Act
    author_email = get_github_author_email("mock_token", "")

    # Assert
    assert author_email == "<not found - empty sha>"


def test_get_pipeline_execution_handles_incorrect_execution_id(
    codepipeline_client_stub,
):
    # Arrange
    from handler import get_pipeline_commit_data

    codepipeline_client_stub.add_client_error(
        "get_pipeline_execution",
        "PipelineExecutionNotFoundException",
        "PipelineExecutionNotFoundException",
    )

    # Act & Assert
    with pytest.raises(ClientError) as e:
        get_pipeline_commit_data(
            "telemetry-terraform-pipeline", "1d18ecc5-2611-436b-9d2f-ba7e9bfc721d"
        )
    assert (
        str(e.value)
        == "An error occurred (PipelineExecutionNotFoundException) when calling the GetPipelineExecution "
        "operation: PipelineExecutionNotFoundException"
    )


def test_get_pipeline_execution_handles_incorrect_pipeline(codepipeline_client_stub):
    # Arrange
    from handler import get_pipeline_commit_data

    codepipeline_client_stub.add_client_error(
        "get_pipeline_execution",
        "PipelineNotFoundException",
        "PipelineNotFoundException",
    )

    # Act & Assert
    with pytest.raises(ClientError) as e:
        get_pipeline_commit_data(
            "non-existent-pipeline", "0d18ecc5-2611-436b-9d2f-ba7e9bfc721d"
        )
    assert (
        str(e.value)
        == "An error occurred (PipelineNotFoundException) when calling the GetPipelineExecution "
        "operation: PipelineNotFoundException"
    )


@patch("handler.get_github_author_email")
def test_handler_golden_path(
    mock_github_author_email,
    ssm,
    codepipeline_client_stub,
    get_pipeline_execution_success_fixture,
    cloudwatch_event_pipeline_failed,
    context,
):
    # Arrange
    from handler import enrich_codepipeline_event

    mock_github_author_email.return_value = (
        "29373851+thinkstack@users.noreply.github.com"
    )
    ssm.put_parameter(Name="telemetry_github_token", Value="token123")
    codepipeline_client_stub.add_response(
        "get_pipeline_execution", get_pipeline_execution_success_fixture
    )

    # Act
    response = enrich_codepipeline_event(cloudwatch_event_pipeline_failed, context)

    # Assert
    assert response is not None
    assert response.get("detail").get("slack_handle") == "lee.myring"
    assert (
        response.get("detail").get("commit_message_summary")
        == "TEL-3481 create pagerduty-config-deployer"
    )
    assert (
        response.get("detail").get("enriched_title")
        == "CodePipeline failed: myPipeline. Committer: @lee.myring Sha: bc051f8d - TEL-3481 create pagerduty-config-deployer"
    )
    assert (
        response.get("detail").get("commit_url")
        == "https://github.com/hmrc/telemetry-terraform/commit/bc051f8d7fbf183dbb840462cb5c17d887964842"
    )


def test_lambda_handler_invalid_event_empty_detail_with_context(
    cloudwatch_event_invalid_no_detail, context
):
    """Test that an event containing unexpected data with lambda context logs appropriately"""
    # Arrange & Act
    from exceptions import EmptyEventDetailException
    from handler import enrich_codepipeline_event

    with pytest.raises(EmptyEventDetailException):
        response = enrich_codepipeline_event(
            cloudwatch_event_invalid_no_detail, context
        )

        # Assert
        assert response is None


def test_lambda_handler_invalid_event_with_no_execution_id(
    cloudwatch_event_invalid_no_execution_id, context
):
    """Test that an event containing missing and required data with lambda context logs appropriately"""
    # Arrange & Act
    from exceptions import NoExecutionIdFoundException
    from handler import enrich_codepipeline_event

    with pytest.raises(NoExecutionIdFoundException):
        response = enrich_codepipeline_event(
            cloudwatch_event_invalid_no_execution_id, context
        )

        # Assert
        assert response is None


@patch("handler.get_github_author_email")
def test_handler_sqs_golden_path(
    mock_github_author_email,
    ssm,
    codepipeline_client_stub,
    get_pipeline_execution_success_fixture,
    sqs_message_containing_cloudwatch_event_pipeline_failed,
    context,
):
    # Arrange
    from handler import enrich_sqs_event

    mock_github_author_email.return_value = "abn@webit4.me"
    # mock_get_github_commit_message_summary.return_value = "[TEL-1234] Here is a commit"
    ssm.put_parameter(Name="telemetry_github_token", Value="token123")
    codepipeline_client_stub.add_response(
        "get_pipeline_execution", get_pipeline_execution_success_fixture
    )

    # Act
    response = enrich_sqs_event(
        sqs_message_containing_cloudwatch_event_pipeline_failed, context
    )

    # Assert
    assert response is not None
    assert response.get("detail").get("slack_handle") == "ali.bahman"
    assert (
        response.get("detail").get("commit_message_summary")
        == "TEL-3481 create pagerduty-config-deployer"
    )
    assert (
        response.get("detail").get("enriched_title")
        == "CodePipeline failed: TEL-2490. Committer: @ali.bahman Sha: bc051f8d - TEL-3481 create pagerduty-config-deployer"
    )
    assert (
        response.get("detail").get("commit_url")
        == "https://github.com/hmrc/telemetry-terraform/commit/bc051f8d7fbf183dbb840462cb5c17d887964842"
    )
