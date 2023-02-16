---
categories: [tech]
date: '2019-06-07'
filename: 2019-06-07-running-keystone-with-docker-c.md
tags:
- openstack
- docker
- keystone
- docker-compose
- tripleo
title: Running Keystone with Docker Compose

---

In this article, we will look at what is necessary to run OpenStack's [Keystone][] service (and the requisite database server) in containers using [Docker Compose][].

[keystone]: https://docs.openstack.org/keystone/latest/
[docker compose]: https://docs.docker.com/compose/

## Running MariaDB

The standard [mariadb docker image][] can be configured via a number of environment variables. It also benefits from persistent volume storage, since in most situations you don't want to lose your data when you remove a container. A simple `docker` command line for starting MariaDB might look something like:

[mariadb docker image]: https://hub.docker.com/_/mariadb/

```
docker run \
  -v mariadb_data:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD=secret.password
  mariadb
```

The above assumes that we have previously created a Docker volume named `mariadb_data` by running:

```
docker volume create mariadb_data
```

An equivalent `docker-compose.yml` would look like this:

```
version: 3

services:
  database:
    image: mariadb
    environment:
      MYSQL_ROOT_PASSWORD: secret.password
    volumes:
      - "mariadb_data:/var/lib/mysql"

volumes:
  mariadb_data:
```

Now, rather than typing a long `docker run` command line (and possibly forgetting something), you can simply run:

```
docker-compose up
```

### Pre-creating a database

For the purposes of setting up Keystone in Docker, we will need to make a few changes. In particular, we will need to have the `mariadb` container create the `keystone` database (and user) for us, and as a matter of best practice we will want to specify an explicit tag for the `mariadb` image rather than relying on the default `latest`.

We can have the `mariadb` image create a database for us at startup by setting the `MYSQL_DATABASE`, `MYSQL_USER`, and `MYSQL_PASSWORD` environment variables:

```
version: 3

services:
  database:
    image: mariadb:10.4.5-bionic
    environment:
      MYSQL_ROOT_PASSWORD: secret.password
      MYSQL_USER: keystone
      MYSQL_PASSWORD: another.password
      MYSQL_DATABASE: keystone
    volumes:
      - "mariadb_data:/var/lib/mysql"

volumes:
  mariadb_data:
```

When the `database` service starts up, it will create a `keystone` database accessible by the `keystone` user.

### Parameterize all the things

The above example is pretty much what we want, but there is one problem: we've hardcoded our passwords (and database name) into the `docker-compose.yml` file, which makes it hard to share: it would be unsuitable for hosting on a public git repository, because anybody who wanted to use it would need to modify the file first, which would make it difficult to contribute changes or bring in new changes from the upstream repository. We can solve that problem by using environment variables in our `docker-compose.yml`. Much like the shell, `docker-compose` will replace an expression of the form `${MY_VARIABLE}` with the value of the `MY_VARIABLE` environment variable. It is possible to provide a fallback value in the event that an environment variable is undefined by writing `${MY_VARIABLE:-some_default_value}`.

You have a couple options for providing values for this variables. You can of course simply set them in the environment, either like this:

    export MY_VARIABLE=some_value

Or as part of the `docker-compose` command line, like this:

    MY_VARIABLE=some_value docker-compose up

Alternatively, you can also set them in a `.env` file in the same directory as your `docker-compose.yml` file; `docker-compose` reads this file automatically when it runs. A `.env` file looks like this:

    MY_VARIABLE=some_value

With the above in mind, we can restructure our example `docker-compose.yml` so that it looks like this:

```
version: 3

services:
  database:
    image: mariadb:${MARIADB_IMAGE_TAG:-10.4.5-bionic}
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_USER: ${KEYSTONE_DB_USER:-keystone}
      MYSQL_PASSWORD: ${KEYSTONE_DB_PASSWORD}
      MYSQL_DATABASE: ${KEYSTONE_DB_NAME:-keystone}
    volumes:
      - "mariadb_data:/var/lib/mysql"

volumes:
  mariadb_data:
```

## Running Keystone

### Selecting a base image

While there is an official MariaDB image available in Docker Hub, there is no such thing as an official Keystone image. A search for `keystone` yields over 300 results. I have elected to use the Keystone image produced as part of the [TripleO][] project, [tripleo-master/centos-binary-keystone]. The `current-rdo` tag follows the head of the Keystone repository, and the images are produced automatically as part of the CI process. Unlike the MariaDB image, which is designed to pretty much be "plug and play", the Keystone image is going to require some configuration before it provides us with a useful service.

[tripleo-master/centos-binary-keystone]: https://hub.docker.com/r/tripleomaster/centos-binary-keystone
[tripleo]: https://wiki.openstack.org/wiki/TripleO
[RDO]: https://www.rdoproject.org/

Using the `centos-binary-keystone` image, there are two required configuration tasks we will have to complete when starting the container:

- We will need to inject an appropriate configuration file to run Keystone as a [WSGI][] binary under Apache [httpd][]. This is certainly not the only way to run Keystone, but the `centos-binary-keystone` image has both `httpd` and `mod_wsgi` installed.

- We will need to inject a minimal configuration for Keystone (for example, we will need to provide Keystone with connection information for the database instance).

[wsgi]: https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface
[httpd]: http://httpd.apache.org/

### Keystone WSGI configuration

We need to configure Keystone as a WSGI service running on port 5000. We will do this with the following configuration file:

```
Listen 5000
ErrorLog "/dev/stderr"
CustomLog "/dev/stderr" combined

<VirtualHost *:5000>
  ServerName keystone
  ServerSignature Off

  DocumentRoot "/var/www/cgi-bin/keystone"

  <Directory "/var/www/cgi-bin/keystone">
    Options Indexes FollowSymLinks MultiViews
    AllowOverride None
    Require all granted
  </Directory>

  WSGIApplicationGroup %{GLOBAL}
  WSGIDaemonProcess keystone_main display-name=keystone-main \
  	processes=12 threads=1 user=keystone group=keystone
  WSGIProcessGroup keystone_main
  WSGIScriptAlias / "/var/www/cgi-bin/keystone/main"
  WSGIPassAuthorization On
</VirtualHost>
```

The easiest way to inject this custom configuration is to bake it into a custom image. Using the `tripleomaster/centos-binary-keystone` base image identified earlier, we can start with a custom `Dockerfile` that looks like this:


```
ARG KEYSTONE_IMAGE_TAG=current-tripleo
FROM tripleomaster/centos-binary-keystone:${KEYSTONE_IMAGE_TAG}

COPY keystone-wsgi-main.conf /etc/httpd/conf.d/keystone-wsgi-main.conf
```

The `ARG` directive permits us to select an image tag via a build argument (but defaults to `current-tripleo`).

We can ask `docker-compose` to build our custom image for us when we run `docker-compose up`. Instead of specifying an `image` as we did with the MariaDB container, we use the `build` directive:

```
[...]
  keystone:
    build:
      context: .
      args:
        KEYSTONE_IMAGE_TAG: current-tripleo
[...]
```

This tells `docker-compose` to use the `Dockerfile` in the current directory (and to set the `KEYSTONE_IMAGE_TAG` build argument to `current-tripleo`). Note that `docker-compose` will only build this image for us by default if it doesn't already exist; we can ask `docker-compose` to build it explicitly by running `docker-compose build`, or by providing the `--build` option to `docker-compose up`.

### Configuring at build time vs run time

In the previous section, we used a `Dockerfile` to build on a selected base image by adding custom content. Other sorts of configuration must happen when the container starts up (for example, we probably want to be able to set passwords at runtime). One way of solving this problem is to embed some scripts into our custom image and then run them when the container starts in order to perform any necessary initialization. 

I have placed some custom scripts and templates into the `runtime` directory and arranged to copy that directory into the custom image like this:

```
ARG KEYSTONE_IMAGE_TAG=current-tripleo
FROM tripleomaster/centos-binary-keystone:${KEYSTONE_IMAGE_TAG}

COPY keystone-wsgi-main.conf /etc/httpd/conf.d/keystone-wsgi-main.conf
COPY runtime /runtime

CMD ["/bin/sh", "/runtime/startup.sh"]
```

The `runtime` directory contains the following files:

- ``runtime/dtu.py`` -- a short Python script for generating files from templates.
- ``runtime/startup.sh`` -- a shell script that performs all the necessary initialization tasks before starting Keystone
- ``runtime/keystone.j2.conf`` -- template for the Keystone configuration file
- ``runtime/clouds.j2.yaml`` -- template for a `clouds.yaml` for use by the `openshift` command line client.

### Starting up

The `startup.sh` script performs the following actions:

1. Generates `/etc/keystone/keystone.conf` from `/runtime/keystone.j2.conf`.

    The file `/runtime/keystone.j2.conf` is a minimal Keystone configuration template. It ensures that Keystone logs to `stderr` (by setting `log_file` to an empty value) and configures the database connection using values from the environment.

    ```
    [DEFAULT]
    debug = {{ environ.KEYSTONE_DEBUG|default('false') }}
    log_file =


    [database]
    {% set keystone_db_user = environ.KEYSTONE_DB_USER|default('keystone') %}
    {% set keystone_db_host = environ.KEYSTONE_DB_HOST|default('localhost') %}
    {% set keystone_db_port = environ.KEYSTONE_DB_PORT|default('3306') %}
    {% set keystone_db_name = environ.KEYSTONE_DB_NAME|default('keystone') %}
    {% set keystone_db_pass = environ.KEYSTONE_DB_PASSWORD|default('insert-password-here') %}
    connection = mysql+pymysql://{{ keystone_db_user }}:{{ keystone_db_pass }}@{{ keystone_db_host }}:{{ keystone_db_port }}/{{ keystone_db_name }}

    [token]
    provider = fernet
    ```

2. Generates `/root/clouds.yaml` from `/runtime/clouds.j2.yaml`.

    The `clouds.yaml` file can be used with to provide authentication information to the `openshift` command line client (and other applications that use the OpenStack Python SDK). We'll see an example of this further on in this article.

3. Initializes Keystone's fernet token mechanism by running `keystone-manage fernet_setup`.

    Keystone supports various token generation mechanisms. Fernet tokens provide some advantages over the older UUID token mechanism. From the [FAQ](fernet-faq):

    > Even though fernet tokens operate very similarly to UUID tokens, they do not require persistence or leverage the configured token persistence driver in any way. The keystone token database no longer suffers bloat as a side effect of authentication. Pruning expired tokens from the token database is no longer required when using fernet tokens. Because fernet tokens do not require persistence, they do not have to be replicated. As long as each keystone node shares the same key repository, fernet tokens can be created and validated instantly across nodes.

4. Initializes the Keystone database schema by running `keystone-manage db_sync`.

    The `db_sync` command creates the database tables that Keystone requires to operate.

5. Creates the Keystone `admin` user and initial service catalog entries by running `keystone-manage bootstrap`

    Before we can authenticate to Keystone, there needs to exist a user with administrative privileges (so that we can create other users, projects, and so forth).

6. Starts `httpd`.

[fernet-faq]: https://docs.openstack.org/keystone/pike/admin/identity-fernet-token-faq.html

### Avoiding race conditions

When we run `docker-compose up`, it will bring up both the `keystone` container and the `database` container in parallel. This is going to cause problems if we try to initialize the Keystone database schema before the database server is actually up and running. There is a `depends_on` keyword that can be used to order the startup of containers in your `docker-compose.yml` file, but this isn't useful to us: this only delays the startup of the dependent container until the indicated container is *running*. It doesn't know anything about application startup, and so it would not wait for the database to be ready.

We need to explicitly wait until we can successfully connect to the database before we can complete initializing the Keystone service. It turns out the easiest solution to this problem is to imply run the database schema initialization in a loop until it is successful, like this:

```
echo "* initializing database schema"
while ! keystone-manage db_sync; do
  echo "! database schema initialization failed; retrying in 5 seconds..."
  sleep 5
done
```

This will attempt the `db_sync` command every five seconds until it is sucessful.

## The final docker-compose file

Taking all of the above into account, this is what the final `docker-compose.yml` file looks like:

```
---
version: "3"

services:
  database:
    image: mariadb:10.4.5-bionic
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_USER: ${KEYSTONE_DB_USER:-keystone}
      MYSQL_PASSWORD: ${KEYSTONE_DB_PASSWORD}
      MYSQL_DATABASE: ${KEYSTONE_DB_NAME:-keystone}
    volumes:
      - mysql:/var/lib/mysql

  keystone:
    build:
      context: .
      args:
        KEYSTONE_IMAGE_TAG: current-tripleo
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      KEYSTONE_ADMIN_PASSWORD: ${KEYSTONE_ADMIN_PASSWORD}
      KEYSTONE_DB_PASSWORD: ${KEYSTONE_DB_PASSWORD}
      KEYSTONE_DB_USER: ${KEYSTONE_DB_USER:-keystone}
      KEYSTONE_DB_NAME: ${KEYSTONE_DB_NAME:-keystone}
      KEYSTONE_DEBUG: ${KEYSTONE_DEBUG:-"false"}
    ports:
      - "127.0.0.1:5000:5000"

volumes:
  mysql:
```

## Interacting with Keystone

Once Keystone is up and running, we can grab the generated `clouds.yaml` file like this:

```
docker-compose exec keystone cat /root/clouds.yaml > clouds.yaml
```

Now we can run the `openstack` command line client:

```
$ export OS_CLOUD=openstack-public
$ openstack catalog list
+----------+----------+-----------------------------------+
| Name     | Type     | Endpoints                         |
+----------+----------+-----------------------------------+
| keystone | identity | RegionOne                         |
|          |          |   internal: http://localhost:5000 |
|          |          | RegionOne                         |
|          |          |   public: http://localhost:5000   |
|          |          |                                   |
+----------+----------+-----------------------------------+
$ openstack user list
+----------------------------------+-------+
| ID                               | Name  |
+----------------------------------+-------+
| e8f460619a854c849feaf278b8d68e2c | admin |
+----------------------------------+-------+
```

## Project sources

You can find everything reference in this article in the [flocx-keystone-dev][] repository.

[flocx-keystone-dev]: https://github.com/cci-moc/flocx-keystone-dev
