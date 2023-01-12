import json


class Helper:
    github_to_slack = {
        "1422984+webit4me@users.noreply.github.com": "ali.bahman",
        "gavD@users.noreply.github.com": "gavin.davies1",
        "29373851+thinkstack@users.noreply.github.com": "lee.myring",
        "22219356+matthew-hollick@users.noreply.github.com": "matthew.hollick",
        "66684341+rizinaa99@users.noreply.github.com": "rizina.khatun",
        "Crumplepang@users.noreply.github.com": "rob.white",
        "18111914+sjpalf@users.noreply.github.com": "stephen.palfreyman",
        "67912934+TimothyFothergill@users.noreply.github.com": "timothy.fothergill",
        "6502426+willemveerman@users.noreply.github.com": "willem.veerman2",
    }

    def __init__(
        self,
        logger,
    ):
        self.logger = logger

    def get_slack_handle(self, github_email):
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
