from __future__ import annotations

import pydantic


class Base(pydantic.BaseModel):
    pass


class Person(Base):
    name: str
    pets: list[Pet]


class Pet(Base):
    name: str
    kind: str
    owner: Person
