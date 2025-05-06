"""
Module for error class declaration
"""
from typing import Union
from requests import Response


class ApiError(Exception):
    def __init__(
        self, resp: Union[Response, dict], message="The api responded with the error"
    ) -> None:
        self.resp = resp
        self.details = ""
        if isinstance(self.resp, Response):
            self.code = self.resp.status_code
            self.details = self.resp.reason

        else:
            self.code = self.resp["status"]
            self.details = self.resp["reason"]

        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.message}: {self.code} \n {self.details}"


class BaseError(Exception):
    def __init__(self, data: dict, message: str) -> None:
        self.data = data
        self.message = message
        super(BaseError, self).__init__(self.message)


class ApiClientError(BaseError):
    def __init__(self, data: dict, message: str) -> None:
        super(ApiClientError, self).__init__(data, message=message)
        self.data = data
        self.message = message


class MangaError(BaseError):
    def __init__(self, data: dict, message: str) -> None:
        super(MangaError, self).__init__(data, message=message)
        self.data = data
        self.message = message


class TagError(BaseError):
    def __init__(self, data: dict, message: str) -> None:
        super(TagError, self).__init__(data, message=message)
        self.data = data
        self.message = message


class ChapterError(BaseError):
    def __init__(self, data: dict, message: str) -> None:
        super(ChapterError, self).__init__(data, message=message)
        self.data = data
        self.message = message


class AuthorError(BaseError):
    def __init__(self, data: dict, message: str) -> None:
        super(AuthorError, self).__init__(data, message=message)
        self.data = data
        self.message = message


class ScanlationGroupError(BaseError):
    def __init__(self, data: dict, message: str) -> None:
        super(ScanlationGroupError, self).__init__(data, message=message)
        self.data = data
        self.message = message


class UserError(BaseError):
    def __init__(self, data: dict, message: str) -> None:
        super(UserError, self).__init__(data, message=message)
        self.data = data
        self.message = message


class CustomListError(BaseError):
    def __init__(self, data: dict, message: str) -> None:
        super(CustomListError, self).__init__(data, message)
        self.data = data
        self.message = message


class CoverArtError(BaseError):
    def __init__(self, data: dict, message: str) -> None:
        super(CoverArtError, self).__init__(data, message=message)
        self.data = data
        self.message = message
