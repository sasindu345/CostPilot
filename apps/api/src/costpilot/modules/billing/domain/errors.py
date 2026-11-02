class BillRejectedError(Exception):
    """This file can never be read, so retrying will not help. The message is shown to users."""
