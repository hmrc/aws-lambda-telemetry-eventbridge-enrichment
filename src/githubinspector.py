from github import Github


class GithubInspector:
    def __init__(self, commit_sha, github_token, github_repo, logger):
        self.logger = logger

        self.author_email = "<not found - empty sha>"
        self.commit_message_subject = "<not found - empty sha>"
        if commit_sha is not None:
            gh = Github(github_token)
            repo = gh.get_repo(github_repo)
            commit = repo.get_commit(sha=commit_sha)
            self.author_email = commit.commit.author.email
            self.commit_message_subject = commit.commit.message.partition("\n")[0]

    def get_author_email():
        return self.author_email

    def get_commit_message_subject():
        return self.commit_message_subject
