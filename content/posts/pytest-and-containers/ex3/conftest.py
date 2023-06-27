import pytest
import docker
import time
import mysql.connector
import string
import random

from contextlib import closing


@pytest.fixture(scope="session")
def docker_client():
    """Return a Docker client"""
    return docker.from_env()


@pytest.fixture(scope="session")
def random_string():
    return "".join(random.choices(string.ascii_letters + string.digits, k=8))


@pytest.fixture(scope="session")
def mariadb_dbpass(random_string):
    return f"secret-{random_string}"


@pytest.fixture(scope="session")
def mariadb_dbname(random_string):
    return f"testdb-{random_string}"


@pytest.fixture(scope="session")
def mariadb_container(
    docker_client,
    random_string,
    mariadb_dbpass,
    mariadb_dbname,
):
    """Create a MariaDB container"""
    container = docker_client.containers.run(
        "docker.io/mariadb:11",
        name=f"mariadb-test-{random_string}",
        detach=True,
        environment={
            "MARIADB_ROOT_PASSWORD": mariadb_dbpass,
            "MYSQL_PWD": mariadb_dbpass,
            "MARIADB_DATABASE": mariadb_dbname,
        },
    )

    yield container

    container.remove(force=True)


@pytest.fixture
def mariadb_host(mariadb_container):
    while True:
        mariadb_container.reload()
        try:
            networks = list(
                mariadb_container.attrs["NetworkSettings"]["Networks"].values()
            )
            addr = networks[0]["IPAddress"]
            return addr
        except KeyError:
            time.sleep(0.5)


@pytest.fixture
def mariadb_connection(mariadb_host, mariadb_dbpass, mariadb_dbname):
    while True:
        try:
            conn = mysql.connector.connect(
                host=mariadb_host,
                user="root",
                password=mariadb_dbpass,
                database=mariadb_dbname,
            )
            return conn
        except mysql.connector.errors.InterfaceError:
            time.sleep(1)


@pytest.fixture
def mariadb_cursor(mariadb_connection):
    with closing(mariadb_connection.cursor()) as cursor:
        yield cursor
