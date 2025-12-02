import json


class Helper:
    github_to_slack = {
        "150913287+wrightda101@users.noreply.github.com": "damon.wright",
        "52657898+dave-miles-hmrc@users.noreply.github.com": "david.miles",
        "9415522+duddingl@users.noreply.github.com": "lyndon.dudding",
        "1253988+nisartahir@users.noreply.github.com": "nisar.tahir",
    }

    def __init__(
        self,
        logger,
    ):
        self.logger = logger

    def get_slack_handle(self, github_email: str) -> str:
        # Default to telemetry-engineers if it's an unknown user
        slack_handle = "telemetry-engineers"
        if github_email in self.github_to_slack:
            slack_handle = self.github_to_slack[github_email]
        self.logger.debug(
            f"Returned Slack handle {slack_handle} for GitHub email {github_email}"
        )
        return slack_handle

    def open_sqs_envelope(self, sqs_message: list) -> dict:
        """
        SQS messages are like an "envelope" wrapping the message we want.
        This method "opens" the "envelope" and returns the message body.
        """
        return json.loads(sqs_message[0].get("body"))
