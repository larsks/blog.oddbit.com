import sqlalchemy
import sqlalchemy.orm

from sqlalchemy.exc import IntegrityError

from example import models
from example import api

engine = sqlalchemy.create_engine("sqlite:///pets.db", echo=True)
models.Base.metadata.create_all(engine)
with sqlalchemy.orm.Session(engine) as session:
    session.begin()
    try:
        api = api.PetShopAPI(session=session)
        api.add_kind("cat")
        api.add_kind("dog")
        api.add_kind("emu")
        api.add_kind("axolotl")
        matches = api.find_person_by_name("Alice")
        if not matches:
            print("Adding Alice")
            alice = api.add_person(name="Alice")
        else:
            alice = matches[0]
    except Exception as err:
        session.rollback()
        raise
    else:
        session.commit()

    for name, kind in (("tom", "cat"), ("jerry", "axolotl")):
        session.begin()
        try:
            kind = api.get_kind_by_name(kind)
            api.add_pet(name, kind=kind, owner=alice)
            session.commit()
        except Exception as err:
            session.rollback()
