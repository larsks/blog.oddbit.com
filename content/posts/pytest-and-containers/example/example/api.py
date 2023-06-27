from . import models


class PetShop:
    def __init__(self, db: models.Database):
        self.db = db

    def addPerson(self, name: str) -> models.Person:
        with models.db_session:
            p = models.Person(name=name)
            self.db.commit()
            return p

    def addKind(self, name: str) -> models.Kind:
        with models.db_session:
            k = models.Kind(name=name)
            self.db.commit()
            return k

    def findKindByName(self, name: str) -> models.Kind:
        with models.db_session:


    def addPet(self, name: str, kind: models.Kind, owner: models.Person) -> models.Pet:
        with models.db_session:
            p = models.Pet(name=name, kind=kind, owner=owner)
            self.db.commit()
            return p
