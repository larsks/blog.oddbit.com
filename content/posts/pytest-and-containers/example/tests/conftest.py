import string
import random
import time
import docker

import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


@pytest.fixture(scope="session")
def mariadb_root_password():
    """Generate a random password for use as the MariaDB root password"""
    return "".join(random.choices(string.ascii_letters, k=15))


@pytest.fixture(scope="session")
def random_suffix():
    """Generate a random suffix to use in naming things"""
    return "".join(random.choices(string.ascii_letters, k=6))


@pytest.fixture(scope="session")
def mariadb_db_name(random_suffix):
    """Return the database name"""
    return f"example-{random_suffix}"


@pytest.fixture(scope="session")
def docker_client():
    """Return a Docker client"""
    return docker.from_env()


@pytest.fixture(scope="session")
def mariadb_container(
    docker_client,
    mariadb_root_password,
    mariadb_db_name,
    random_suffix,
):
    """Create a MariaDB container, and remove it when tests are complete"""
    container = docker_client.containers.run(
        "docker.io/mariadb:11",
        name=f"mariadb-{random_suffix}",
        detach=True,
        environment={
            "MARIADB_ROOT_PASSWORD": mariadb_root_password,
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
def mariadb_engine(mariadb_host, mariadb_root_password, mariadb_db_name):
    """Return a sqlalchemy Engine for interacting with the containerized mariadb server"""
    engine = create_engine(
        f"mariadb+pymysql://root:{mariadb_root_password}@{mariadb_host}:3306/{mariadb_db_name}"
    )
    yield engine


@pytest.fixture
def mariadb_connection(mariadb_engine):
    """Wait until mariadb is ready to service connections, then return a
    sqlalchemy connection"""
    while True:
        try:
            with mariadb_engine.connect() as con:
                # This will raise an OperationalError if the database isn't
                # ready to accept connections.
                con.execute(text("select 1"))
                yield con
                break
        except OperationalError:
            time.sleep(1)
