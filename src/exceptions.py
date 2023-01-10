class EmptyEventDetailException(Exception):
    """Is raised if the event passed to the lambda has no detail object."""

    pass


class NoExecutionIdFoundException(Exception):
    """Is raised when no execution id is found in the event."""

    pass
