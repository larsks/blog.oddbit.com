import string
import random
import time
import docker
from contextlib import closing

import mysql.connector
import pytest

import example.dbapi


@pytest.fixture(scope="session")
def session_suffix():
    """Generate a random suffix to use in naming things"""
    return "".join(random.choices(string.ascii_letters, k=6))


@pytest.fixture(scope="session")
def mariadb_db_user(session_suffix):
    """Return the database user"""
    return f"testuser-{session_suffix}"


@pytest.fixture(scope="session")
def mariadb_db_password(session_suffix):
    """Return a password for the database user"""
    return f"secret-{session_suffix}"


@pytest.fixture(scope="session")
def mariadb_root_password(session_suffix):
    """Return a password for the database user"""
    return f"root-secret-{session_suffix}"


@pytest.fixture(scope="session")
def mariadb_db_name(session_suffix):
    """Return the database name"""
    return f"testdb-{session_suffix}"


@pytest.fixture(scope="session")
def docker_client():
    """Return a Docker client"""
    return docker.from_env()


@pytest.fixture(scope="session")
def mariadb_container(
    docker_client,
    mariadb_root_password,
    mariadb_db_name,
    mariadb_db_user,
    mariadb_db_password,
):
    """Create a MariaDB container, and remove it when tests are complete"""
    container = docker_client.containers.run(
        "docker.io/mariadb:11",
        name=mariadb_db_name,
        detach=True,
        environment={
            "MARIADB_ROOT_PASSWORD": mariadb_root_password,
            "MARIADB_USER": mariadb_db_user,
            "MARIADB_PASSWORD": mariadb_db_password,
            "MYSQL_PWD": mariadb_root_password,
            "MARIADB_DATABASE": mariadb_db_name,
        },
    )

    yield container

    container.remove(force=True)


@pytest.fixture
def mariadb_host(mariadb_container):
    """Wait until the container has an address and then return that address"""
    while not mariadb_container.attrs["NetworkSettings"]["IPAddress"]:
        mariadb_container.reload()

    yield mariadb_container.attrs["NetworkSettings"]["IPAddress"]


@pytest.fixture
def mariadb_connection(
    mariadb_db_user, mariadb_db_password, mariadb_db_name, mariadb_host
):
    while True:
        try:
            cnx = mysql.connector.connect(
                user=mariadb_db_user,
                password=mariadb_db_password,
                host=mariadb_host,
                database=mariadb_db_name,
            )

            # Ensure a simple select statement is successful
            try:
                cursor = cnx.cursor()
                cursor.execute("select 1")
                cursor.fetchall()
                break
            finally:
                cursor.close()
        except mysql.connector.errors.InterfaceError:
            time.sleep(1)

    with closing(cnx):
        yield cnx


@pytest.fixture
def mariadb_cursor(mariadb_connection):
    with closing(mariadb_connection.cursor()) as cursor:
        yield cursor


@pytest.fixture
def dbapi(mariadb_connection):
    db = example.dbapi.PetShopDB(mariadb_connection)
    db.create_tables()
    return db
