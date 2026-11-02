"""Errors that stop a command with a clear message and a non-zero exit code."""


class AdReceiptsError(Exception):
    """A problem the user can understand and act on."""

    exit_code = 1

    def __init__(self, message, hint=None):
        super().__init__(message)
        self.message = message
        self.hint = hint


class SafetyStop(AdReceiptsError):
    """A safety rule refused the action. Nothing was written to the phone."""

    exit_code = 2


class RunStopped(AdReceiptsError):
    """A run was stopped part-way. The affected batch was undone."""

    exit_code = 3


class AdbError(AdReceiptsError):
    """adb is missing, the phone is not reachable, or a command failed."""

    exit_code = 4
