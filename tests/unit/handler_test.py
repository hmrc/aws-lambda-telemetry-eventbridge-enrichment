from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError


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


def test_get_pipeline_execution_succeeds(
    codepipeline_client_stub, get_pipeline_execution_success_fixture
):
    # Arrange
    from handler import get_pipeline_commit_sha

    codepipeline_client_stub.add_response(
        "get_pipeline_execution", get_pipeline_execution_success_fixture
    )

    # Act
    git_revision_id = get_pipeline_commit_sha(
        "telemetry-terraform-pipeline", "0d18ecc5-2611-436b-9d2f-ba7e9bfc721d"
    )

    # Assert
    assert git_revision_id == "bc051f8d7fbf183dbb840462cb5c17d887964842"


def test_get_pipeline_execution_handles_incorrect_execution_id(
    codepipeline_client_stub,
):
    # Arrange
    from handler import get_pipeline_commit_sha

    codepipeline_client_stub.add_client_error(
        "get_pipeline_execution",
        "PipelineExecutionNotFoundException",
        "PipelineExecutionNotFoundException",
    )

    # Act & Assert
    with pytest.raises(ClientError) as e:
        get_pipeline_commit_sha(
            "telemetry-terraform-pipeline", "1d18ecc5-2611-436b-9d2f-ba7e9bfc721d"
        )
    assert (
        str(e.value)
        == "An error occurred (PipelineExecutionNotFoundException) when calling the GetPipelineExecution "
        "operation: PipelineExecutionNotFoundException"
    )


def test_get_pipeline_execution_handles_incorrect_pipeline(codepipeline_client_stub):
    # Arrange
    from handler import get_pipeline_commit_sha

    codepipeline_client_stub.add_client_error(
        "get_pipeline_execution",
        "PipelineNotFoundException",
        "PipelineNotFoundException",
    )

    # Act & Assert
    with pytest.raises(ClientError) as e:
        get_pipeline_commit_sha(
            "non-existent-pipeline", "0d18ecc5-2611-436b-9d2f-ba7e9bfc721d"
        )
    assert (
        str(e.value)
        == "An error occurred (PipelineNotFoundException) when calling the GetPipelineExecution "
        "operation: PipelineNotFoundException"
    )


@patch("handler.get_github_author_email")
def test_handler_golden_path(
    mock_github,
    ssm,
    codepipeline_client_stub,
    get_pipeline_execution_success_fixture,
    cloudwatch_event_pipeline_failed,
    context,
):
    # Arrange
    from handler import enrich_codepipeline_event

    mock_github.return_value = "29373851+thinkstack@users.noreply.github.com"
    ssm.put_parameter(Name="telemetry_github_token", Value="token123")
    codepipeline_client_stub.add_response(
        "get_pipeline_execution", get_pipeline_execution_success_fixture
    )

    # Act
    response = enrich_codepipeline_event(cloudwatch_event_pipeline_failed, context)

    # Assert
    assert response is not None
    assert response.get("detail").get("slack_handle") == "lee.myring"


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
