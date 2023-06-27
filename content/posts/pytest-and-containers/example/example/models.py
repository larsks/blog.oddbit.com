from urllib import parse as urlparse
from pony.orm import Database, Required, PrimaryKey, Set, db_session

db = Database()


class Person(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    pets = Set("Pet")


class Kind(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    pets = Set("Pet")


class Pet(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    kind = Required(Kind)
    owner = Required(Person)


def init(dburi):
    parsed = urlparse.urlparse(dburi)
    if parsed.scheme != "mysql":
        raise ValueError(parsed.scheme)

    userpass, hostport = parsed.netloc.split("@", 1)
    try:
        host, portstr = hostport.split(":")
        port = int(portstr)
    except ValueError:
        host = hostport
        port = 3306
    username, password = userpass.split(":", 1)

    connectionSpec = {
        "provider": parsed.scheme,
        "host": host,
        "port": port,
        "user": username,
        "passwd": password,
        "db": parsed.path[1:],
    }

    db.bind(**connectionSpec)
    db.generate_mapping(create_tables=True)
