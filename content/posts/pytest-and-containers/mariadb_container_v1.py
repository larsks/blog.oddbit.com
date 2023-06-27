import docker
import pytest


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

    return container
