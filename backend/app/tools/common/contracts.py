from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from app.db.database import Database


class EmptyInput(BaseModel):
    pass


class SearchInput(BaseModel):
    query: str = ""


class IdInput(BaseModel):
    id: str = Field(min_length=1)


class LabelInput(IdInput):
    label: str = Field(min_length=1, max_length=80)


class TrackerInput(IdInput):
    perk: str = Field(min_length=1, max_length=300)


class ContentInput(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


@dataclass(frozen=True)
class ToolOutput:
    data: Any
    summary: str


@dataclass(frozen=True)
class ToolSpec:
    name: str
    agent: str
    mutating: bool
    input_type: type[BaseModel]
    invoke: Callable[[Database, BaseModel], ToolOutput]
