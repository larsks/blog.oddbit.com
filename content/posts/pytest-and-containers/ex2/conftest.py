import pytest
import docker
import time
import mysql.connector

from contextlib import closing


@pytest.fixture(scope="session")
def docker_client():
    """Return a Docker client"""
    return docker.from_env()


@pytest.fixture
def mariadb_container(
    docker_client,
):
    """Create a MariaDB container"""
    container = docker_client.containers.run(
        "docker.io/mariadb:11",
        detach=True,
        environment={
            "MARIADB_ROOT_PASSWORD": "secret",
            "MYSQL_PWD": "secret",
            "MARIADB_DATABASE": "testdb",
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
def mariadb_connection(mariadb_host):
    while True:
        try:
            conn = mysql.connector.connect(
                host=mariadb_host, user="root", password="secret", database="testdb"
            )
            return conn
        except mysql.connector.errors.InterfaceError:
            time.sleep(1)


@pytest.fixture
def mariadb_cursor(mariadb_connection):
    with closing(mariadb_connection.cursor()) as cursor:
        yield cursor
