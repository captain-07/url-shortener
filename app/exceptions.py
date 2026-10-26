from datetime import datetime


class LinkNotFoundError(Exception):
    def __init__(self, code: str):
        self.code = code


class LinkExpiredError(Exception):
    def __init__(self, code: str, expired_at: datetime):
        self.code = code
        self.expired_at = expired_at


class AliasTakenError(Exception):
    def __init__(self, alias: str):
        self.alias = alias


class CodeGenerationError(Exception):
    """Could not find a free short code after several attempts."""