from contextlib import closing, contextmanager

tables = [
    """
create table if not exists people(
    id int not null auto_increment primary key,
    name varchar(40)
    )
""",
    """
create table if not exists kinds(
    id int not null auto_increment primary key,
    name varchar(40) unique
)
""",
    """
create table if not exists pets(
    id int not null auto_increment primary key,
    name varchar(40),
    kind_id int not null references kinds(id),
    owner_id int not null references people(id),
    unique(owner_id, name)
)
""",
]


@contextmanager
def committing(cnx):
    with closing(cnx.cursor()) as cursor:
        yield cursor

    cnx.commit()


class PetShopDB:
    def __init__(self, cnx):
        self.cnx = cnx

    def create_tables(self):
        with closing(self.cnx.cursor()) as cursor:
            for table in tables:
                cursor.execute(table)

    def add_person(self, name):
        with committing(self.cnx) as cursor:
            cursor.execute("insert into people (name) values (%s)", (name,))

    def find_person(self, name):
        with closing(self.cnx.cursor()) as cursor:
            cursor.execute("select * from people where name = %s", (name,))
            return cursor.fetchall()

    def delete_person(self, name):
        with committing(self.cnx) as cursor:
            cursor.execute("delete from people where name = %s", (name,))

    def add_kind(self, name):
        with committing(self.cnx) as cursor:
            try:
                self.get_kind(name)
            except KeyError:
                cursor.execute("insert into kinds (name) values (%s)", (name,))

    def get_kind(self, name):
        with closing(self.cnx.cursor()) as cursor:
            cursor.execute("select * from kinds where name = %s", (name,))
            res = cursor.fetchall()

            if not res:
                raise KeyError(name)
            if len(res) > 1:
                raise ValueError(f"found multiple kinds named {name}")

            return res[0]

    def add_pet(self, person_id, kind_id, name):
        with committing(self.cnx) as cursor:
            cursor.execute(
                "insert into pets (name, kind_id, owner_id) values (%s, %s, %s)",
                (name, kind_id, person_id),
            )

    def get_pets(self, person_id):
        with closing(self.cnx.cursor()) as cursor:
            cursor.execute("select * from pets where owner_id = %s", (person_id,))
            res = cursor.fetchall()
