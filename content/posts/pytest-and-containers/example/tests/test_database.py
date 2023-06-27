import random
import string
import pytest

from mysql.connector.errors import IntegrityError


@pytest.fixture
def testperson():
    return f"testperson-{''.join(random.choices(string.ascii_letters, k=6))}"


@pytest.fixture
def testkind():
    return f"testkind-{''.join(random.choices(string.ascii_letters, k=6))}"


@pytest.fixture
def testpet():
    return f"testpet-{''.join(random.choices(string.ascii_letters, k=6))}"


def test_add_person(dbapi, testperson):
    """ensure that we can add a person"""

    dbapi.add_person(testperson)
    res = dbapi.find_person(testperson)
    assert len(res) == 1
    assert res[0][1] == testperson


def test_delete_person_does_not_exist(dbapi, testperson):
    """ensure that we can create and delete a person"""

    dbapi.add_person(testperson)
    dbapi.delete_person(testperson)
    res = dbapi.find_person(testperson)
    assert not res


def test_insert_multiple_kind(dbapi, testkind):
    """we should be able to call add_kind with the same value multiple times
    without raising an integrityerror"""

    dbapi.add_kind(testkind)
    dbapi.add_kind(testkind)
    dbapi.get_kind(testkind)


def test_only_one_named_pet(dbapi, testperson, testpet, testkind):
    """we only allow a person to have a single pet with a given name"""

    dbapi.add_kind(testkind)
    dbapi.add_person(testperson)

    kind = dbapi.get_kind(testkind)
    person = dbapi.find_person(testperson)[0]

    dbapi.add_pet(person[0], kind[0], testpet)

    with pytest.raises(IntegrityError):
        dbapi.add_pet(person[0], kind[0], testpet)
