from pydantic import BaseModel as BaseModel_, Field  # noqa: F401


class BaseModel(BaseModel_):
    class Config:
        underscore_attrs_are_private = False