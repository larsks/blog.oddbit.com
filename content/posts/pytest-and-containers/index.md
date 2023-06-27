---
categories: [tech]
title: Managing containers with Pytest fixtures
date: "2023-07-15"
tags:
  - python
  - pytest
  - fixtures
  - containers
---

A [software fixture][wikipedia] "sets up a system for the software testing process by initializing it, thereby satisfying any preconditions the system may have". They allow us to perform setup and teardown tasks, provide state or set up services required for our tests, and perform other initialization tasks. In this article, we're going to explore how to use fixtures in [Pytest][] to create and tear down containers as part of a test run.

[wikipedia]: https://en.wikipedia.org/wiki/Test_fixture#Software
[pytest]: https://docs.pytest.org/en/7.4.x/


## Pytest Fixtures

Pytest [fixtures][] are created through the use of the `fixture` decorator. A fixture is accessed by including a function parameter with the fixture name in our test functions. For example, if we define an `example` fixture:

[fixtures]: https://docs.pytest.org/en/6.2.x/fixture.html

```
@pytest.fixture
def example():
    return "hello world"
```

Then we can write a test function like this:

```
def test_something(example):
    ...
```

And it will receive the string "hello world" as the value of the `example` parameter.

There are a number of built-in fixtures available; for example, the `tmp_path` fixture provides access to a temporary directory that is unique to each test function. The following function would create a file named `myfile` in the temporary directory; the file (in fact, the entire directory) will be removed automatically when the function completes:

```python
def test_something(tmp_path):
    with (tmp_path / "myfile").open() as fd:
        fd.write('this is a test')
```

A fixture can declare a [scope][]; the default is the `function` scope -- a new value will be generated for each function. A fixture can also be declared with a scope of `class`, `module`, `package`, or `session` (where "session" means, effectively, a distinct run of `pytest`).

[scope]: https://docs.pytest.org/en/6.2.x/fixture.html#scope-sharing-fixtures-across-classes-modules-packages-or-session

Fixtures can be located in the same files as your tests, or they can be placed in a [`conftest.py`][conftest] file where they can be shared between multiple sets of tests.

[conftest]: https://docs.pytest.org/en/6.2.x/fixture.html#scope-sharing-fixtures-across-classes-modules-packages-or-session

## Communicating with Docker

In order to manage containers as part of the test process we're going to need to interact with Docker. While we could call out to the `docker` CLI from our tests, a more graceful solution is to use the [Docker client for Python][docker-py]. That means we'll need a Docker client instance, so we start with a very simple fixture:

```python
import docker

@pytest.fixture(scope="session")
def docker_client():
    """Return a Docker client"""
    return docker.from_env()
```

This returns a Docker client initialized using values from the environment (in other words, it behaves very much like the `docker` cli).

I've made this a `session` scoped fixture (which means we create one Docker client object at per pytest run, and every test using this fixture will receive the same object). This makes sense in general because a Docker client is stateless; there isn't any data we need to reset between tests. 

[docker-py]: https://docker-py.readthedocs.io/en/stable/

## Starting a container, version 1

For the purposes of this article, let's assume we want to spin up a MariaDB server in a container. From the command line we might run something like this:

```
docker run -d \
  -e MARIADB_ROOT_PASSWORD=secret \
  -e MARIADB_USER=testuser \
  -e MARIADB_DATABASE=testdb \
  mariadb:10
```

Looking through the Docker [python API documentation][], a naïve Python equivalent might look like this:

[python api documentation]: https://docker-py.readthedocs.io/en/stable/

{{< code language="python" >}}
{{% include file="mariadb_container_v1.py" %}}
{{< /code >}}

This works, but it's not great. In particular, the container we create will hang around until we remove it manually, since we didn't arrange to remove the container on completion. Since this is a `function` scoped fixture, we would end up with one container per test (potentially leading to hundreds of containers running for a large test suite).

## Starting a container, version 2

Let's take care of the biggest problem with the previous implementation and ensure that our containers get cleaned up. We can add cleanup code to a fixture by using a [yield fixture][]; instead of `return`-ing a value, we [`yield`][yield] a value, and any cleanup code after the `yield` statement runs when the fixture is no longer in scope.

[yield fixture]: https://docs.pytest.org/en/6.2.x/fixture.html#yield-fixtures-recommended
[yield]: https://docs.python.org/3/reference/expressions.html#yield-expressions

That might look like:

{{< code language="python" >}}
{{% include file="mariadb_container_v2.py" %}}
{{< /code >}}

That's better, but we're not out of the woods yet. How would we use this fixture in a test? Maybe we would try something like this:

{{< code language="python" >}}
{{% include file="ex1/test_mariadb.py" %}}
{{< /code >}}

First of all, that's not a great test; there's too much setup happening in the test that we would have to repeat before every additional test. And more importantly, if you were to try to run that test it would probably fail with:

```
E           mysql.connector.errors.InterfaceError: 2003: Can't connect to MySQL
server on '172.17.0.2:3306' (111 Connection refused)
```

The problem is that when we start the MariaDB container, MariaDB isn't ready to handle connections immediately. It takes a couple of seconds after starting the container before the server is ready. Because we haven't accounted for that in our test, there's nothing listening when we try to connect.

## A step back and a moving forward

To resolve the issues in the previous example, let's first take a step back. For our test, we don't actually *want* a container; what we want is the ability to perform SQL queries in our test with a minimal amount of boilerplate. Ideally, our test would look more like this:

```python
def test_simple_select(mariadb_cursor):
    curs.execute('select 1')
    res = curs.fetchone()
    assert res[0] == 1
```

How do we get there?

Working backwards, we would need a `mariadb_cursor` fixture:

```python
@pytest.fixture
def mariadb_cursor(...):
    ...
```

But to get a database cursor, we need a database connection:

```python
@pytest.fixture
def mariadb_connection(...):
    ...
```

And to create a database connection, we need to know the address of the database server:

```python
@pytest.fixture
def mariadb_host(...):
  ...
```

Let's start filling in all those ellipses.

What would the `mariadb_host` fixture look like? We saw in our earlier test code how to get the address of a Docker container. Much like the situation with the database server, we want to account for the fact that it might take a nonzero amount of time for the container network setup to complete, so we can use a simple loop in which we check for the address and return it if it's available, otherwise sleep a bit and try again:


```python
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
```

This works by repeatedly refreshing information about the container until we can find an ip address.

Now that we have the address of the database server, we can create a connection:

```python
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
```

The logic here is very similar; we keep attempting to establish a connection until we're successful, at which point we return the connection object.

Now that we have a fixture that gives us a functioning database connection, we can use that to acquire a cursor:

```python
from contextlib import closing

@pytest.fixture
def mariadb_cursor(mariadb_connection):
    with closing(mariadb_connection.cursor()) as cursor:
        yield cursor
```

The [`closing`][closing] method from the `contextlib` module returns a [context manager][] that calls the `close` method on the given object when leaving the `with` context; this ensures that the cursor is closed when we're done with it. We could have accomplished the same thing by writing this instead:

```python
def mariadb_cursor(mariadb_connection):
    cursor = mariadb_connection.cursor()
    yield cursor
    cursor.close()
```

[closing]: https://docs.python.org/3/library/contextlib.html#contextlib.closing
[context manager]: https://docs.python.org/3/library/stdtypes.html#context-manager-types

Putting all of this together gets us a `conftest.py` that looks something like:

{{< code language="python" >}}
{{% include file="ex2/conftest.py" %}}
{{< /code >}}

And *that* allows us to dramatically simplify our test:

{{< code language="python" >}}
{{% include file="ex2/test_mariadb.py" %}}
{{< /code >}}

So we've accomplished our goal.

## Additional improvements

### Things we're ignoring

In order to keep this post to a reasonable size, we haven't bothered to create an actual application, which means we haven't had to worry about things like initializing the database schema. In reality, we would probably handle that in a new or existing fixture.

### Replaced hardcoded values

While our fixture does the job, we're using a number of hardcoded values (for the username, the database name, the password, etc). This isn't inherently bad for a test environment, but it can sometimes mask errors in our code (for example, if we pick values that match default values in our code, we might miss errors that crop up when using non-default values).

We can replace fixed strings with fixtures that produce random values (or values with a random component, if we want something a little more human readable). In the following example, we have a `random_string` fixture that produces an 8 character random string, and then we use that to produce a password and a database name:

```python
import string
import random


@pytest.fixture
def random_string():
    return "".join(random.choices(string.ascii_letters + string.digits, k=8))


@pytest.fixture
def mariadb_dbpass(random_string):
    return f"secret-{random_string}"


@pytest.fixture
def mariadb_dbname(random_string):
    return f"testdb-{random_string}"
```

We would incorporate these into our existing fixtures wherever we need the database password or name:

```python
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
```

(and so forth)

### Consider a session scoped container

The fixtures we've developed in this post have all been `function` scoped, which means that we're creating and tearing down a container for every single function. This will substantially increase the runtime of our tests. We may want to consider using `session` scoped fixtures instead; this would bring up a container and it use it for all our tests, only cleaning it up at the end of the test run.

The advantage here is that the impact on the test run time is minimal. The disadvantage is that we have to be very careful about the interaction between tests, since we would no longer be starting each test with a clean version of the database.

Keep in mind that in Pytest, a fixture can only reference other fixtures that come from the same or "broader" scope (so, a `function` scoped fixture can use a `session` scoped fixture, but the opposite is not true). In particular, that means if we were to make our `mariadb_container` fixture `session`-scoped, we would need to make the same change to its dependencies (`mariadb_dbname`, `mariadb_dbpass`, etc).

---

You can find a version of `conftest.py` with these changes [here][conftest.py].

[conftest.py]: ex3/conftest.py
