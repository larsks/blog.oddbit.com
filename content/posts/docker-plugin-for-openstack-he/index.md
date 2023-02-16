---
categories: [tech]
aliases: ["/2014/08/30/docker-plugin-for-openstack-he/"]
title: Docker plugin for OpenStack Heat
date: "2014-08-30"
tags:
  - docker
  - openstack
  - heat
  - orchestration
  - pull-request
---

I have been looking at both Docker and OpenStack recently. In my [last
post][] I talked a little about the [Docker driver for Nova][]; in
this post I'll be taking an in-depth look at the Docker plugin for
Heat, which has been available [since the Icehouse release][release] but is
surprisingly under-documented.

[last post]: {{< ref "novadocker-and-environment-var" >}}
[docker driver for nova]: https://github.com/stackforge/nova-docker
[release]: https://blog.docker.com/2014/03/docker-will-be-in-openstack-icehouse/

The [release announcement][release] on the Docker blog includes an
example Heat template, but it is unfortunately grossly inaccurate and
has led many people astray.  In particular:

- It purports to but does not actually install Docker, due to a basic
  [YAML][] syntax error, and
- Even if you were to fix that problem, the lack of synchronization
  between the two resources in the template would mean that you would
  never be able to successfully launch a container.

[YAML]: http://en.wikipedia.org/wiki/YAML

In this post, I will present a fully functional example that will work
with the Icehouse release of Heat.  We will install the Docker plugin
for Heat, then write a template that will (a) launch a Fedora 20
server and automatically install Docker, and then (b) use the Docker
plugin to launch some containers on that server.

The [complete template][] referenced in this article can be found on GitHub:

- <https://github.com/larsks/heat-docker-example>

[complete template]: https://github.com/larsks/heat-docker-example

## Installing the Docker plugin

The first thing we need to do is install the Docker plugin.  I am
running [RDO][] packages for Icehouse locally, which do not include
the Docker plugin.  We'r going to install the plugin from the Heat
sources.

[rdo]: http://openstack.redhat.com/

1. Download the Heat repository:

        $ git clone https://github.com/openstack/heat.git
        Cloning into 'heat'...
        remote: Counting objects: 50382, done.
        remote: Compressing objects: 100% (22/22), done.
        remote: Total 50382 (delta 7), reused 1 (delta 0)
        Receiving objects: 100% (50382/50382), 19.84 MiB | 1.81 MiB/s, done.
        Resolving deltas: 100% (34117/34117), done.
        Checking connectivity... done.

1. This will result in a directory called `heat` in your current
   working directory.  Change into this directory:

        $ cd heat

1. Patch the Docker plugin.

     You have now checked out the `master` branch of the Heat
   repository; this is the most recent code committed to the project.
   At this point we could check out the `stable/icehouse` branch of
   the repository to get the version of the plugin released at the
   same time as the version of Heat that we're running, but we would
   find that the Docker plugin was, at that point in time, somewhat
   crippled; in particular:

     - It does not support mapping container ports to host ports, so
       there is no easy way to expose container services for external
       access, and

     - It does not know how to automatically `pull` missing images, so
       you must arrange to run `docker pull` a priori for each image you
       plan to use in your Heat template.

     That would make us sad, so instead we're going to use the plugin
     from the `master` branch, which only requires a trivial change in
     order to work with the Icehouse release of Heat.

     Look at the file
     `contrib/heat_docker/heat_docker/resources/docker_container.py`.
     Locate the following line:

        attributes_schema = {

     Add a line immediately before that so that the file look like
     this:

        attributes.Schema = lambda x: x
        attributes_schema = {

     If you're curious, here is what we accomplished with that
     additional line:
     
     The code following that point contains multiple stanzas of the
     form:

        INFO: attributes.Schema(
            _('Container info.')
        ),

     In Icehouse, the `heat.engine.attributes` module does not have a
     `Schema` class so this fails.  Our patch above adds a module
     member named `Schema` that simply returns it's arguments (that
     is, it is an identity function).

     (**NB**: At the time this was written, Heat's `master` branch was
     at `a767880`.)

1. Install the Docker plugin into your Heat plugin directory, which
   on my system is `/usr/lib/heat` (you can set this explicitly using
   the `plugin_dirs` directive in `/etc/heat/heat.conf`):

        $ rsync -a --exclude=tests/ contrib/heat_docker/heat_docker \
            /usr/lib/heat

    We're excluding the `tests` directory here because it has
    additional prerequisites that aren't operationally necessary but
    that will prevent Heat from starting up if they are missing.

1. Restart your `heat-engine` service.  On Fedora, that would be:

        # systemctl restart openstack-heat-engine

1. Verify that the new `DockerInc::Docker::Container` resource is
   available:

        $ heat resource-type-list | grep Docker
        | DockerInc::Docker::Container             |

## Templates: Installing docker

We would like our template to automatically install Docker on a Nova
server.  The example in the [Docker blog][release] mentioned earlier
attempts to do this by setting the `user_data` parameter of a
`OS::Nova::Server` resource like this:

    user_data: #include https://get.docker.io
    
Unfortunately, an unquoted `#` introduces a comment in [YAML][], so
this is completely ignored.  It would be written more correctly like
this (the `|` introduces a block of literal text):

    user_data: |
      #include https://get.docker.io

Or possibly like this, although this would restrict you to a single
line and thus wouldn't be used much in practice:

    user_data: "#include https://get.docker.io"

And, all other things being correct, this would install Docker on a
system...but would not necessarily start it, nor would it configure
Docker to listen on a TCP socket.  On my Fedora system, I ended up
creating the following `user_data` script:

    #!/bin/sh
    
    yum -y upgrade

    # I have occasionally seen 'yum install' fail with errors
    # trying to contact mirrors.  Because it can be a pain to
    # delete and re-create the stack, just loop here until it
    # succeeds.
    while :; do
      yum -y install docker-io
      [ -x /usr/bin/docker ] && break
      sleep 5
    done

    # Add a tcp socket for docker
    cat > /etc/systemd/system/docker-tcp.socket <<EOF
    [Unit]
    Description=Docker remote access socket

    [Socket]
    ListenStream=2375
    BindIPv6Only=both
    Service=docker.service

    [Install]
    WantedBy=sockets.target
    EOF

    # Start and enable the docker service.
    for sock in docker.socket docker-tcp.socket; do
      systemctl start $sock
      systemctl enable $sock
    done

This takes care of making sure our packages are current, installing
Docker, and arranging for it to listen on a tcp socket.  For that last
bit, we're creating a new `systemd` socket file
(`/etc/systemd/system/docker-tcp.socket`), which means that `systemd`
will actually open the socket for listening and start `docker` if
necessary when a client connects.

## Templates: Synchronizing resources

In our Heat template, we are starting a Nova server that will run
Docker, and then we are instantiating one or more Docker containers
that will run on this server.  This means that timing is suddenly very
important.  If we use the `user_data` script as presented in the
previous section, we would probably end up with an error like this in
our `heat-engine.log`:

    2014-08-29 17:10:37.598 15525 TRACE heat.engine.resource ConnectionError:
      HTTPConnectionPool(host='192.168.200.11', port=2375): Max retries exceeded
      with url: /v1.12/containers/create (Caused by <class 'socket.error'>:
      [Errno 113] EHOSTUNREACH)

This happens because it takes *time* to install packages.  Absent any
dependencies, Heat creates resources in parallel, so Heat is happily
trying to spawn our Docker containers when our server is still
fetching the Docker package.

Heat does have a `depends_on` property that can be applied to
resources.  For example, if we have:

    docker_server:
      type: "OS::Nova::Server"

We can make a Docker container depend on that resource:

    docker_container_mysql:
      type: "DockerInc::Docker::Container"
      depends_on: 
        - docker_server

Looks good, but this does not, in fact, help us.  From Heat's
perspective, the dependency is satisfied as soon as the Nova server
*boots*, so really we're back where we started.

The Heat solution to this is the `AWS::CloudFormation::WaitCondition`
resource (and its boon companion, the and
`AWS::CloudFormation::WaitConditionHandle` resource).  A
`WaitCondition` is a resource this is not "created" until it has
received an external signal.  We define a wait condition like this:

    docker_wait_handle:
      type: "AWS::CloudFormation::WaitConditionHandle"

    docker_wait_condition:
      type: "AWS::CloudFormation::WaitCondition"
      depends_on:
        - docker_server
      properties:
        Handle:
          get_resource: docker_wait_handle
        Timeout: "6000"

And then we make our container depend on the wait condition:

    docker_container_mysql:
      type: "DockerInc::Docker::Container"
      depends_on: 
        - docker_wait_condition

With this in place, Heat will not attempt to create the Docker
container until we signal the wait condition resource.  In order to do
that, we need to modify our `user_data` script to embed the
notification URL generated by heat.  We'll use both the `get_resource`
and `str_replace` [intrinsic function][] in order to generate the appropriate
script:

[intrinsic function]: http://docs.openstack.org/developer/heat/template_guide/hot_spec.html#intrinsic-functions

      user_data:
        # We're using Heat's 'str_replace' function in order to
        # substitute into this script the Heat-generated URL for
        # signaling the docker_wait_condition resource.
        str_replace:
          template: |
            #!/bin/sh
            
            yum -y upgrade

            # I have occasionally seen 'yum install' fail with errors
            # trying to contact mirrors.  Because it can be a pain to
            # delete and re-create the stack, just loop here until it
            # succeeds.
            while :; do
              yum -y install docker-io
              [ -x /usr/bin/docker ] && break
              sleep 5
            done

            # Add a tcp socket for docker
            cat > /etc/systemd/system/docker-tcp.socket <<EOF
            [Unit]
            Description=Docker remote access socket

            [Socket]
            ListenStream=2375
            BindIPv6Only=both
            Service=docker.service

            [Install]
            WantedBy=sockets.target
            EOF

            # Start and enable the docker service.
            for sock in docker.socket docker-tcp.socket; do
              systemctl start $sock
              systemctl enable $sock
            done

            # Signal heat that we are finished settings things up.
            cfn-signal -e0 --data 'OK' -r 'Setup complete' '$WAIT_HANDLE'
          params:
            "$WAIT_HANDLE":
              get_resource: docker_wait_handle

The `str_replace` function probably deserves a closer look; the
general format is:

    str_replace:
      template:
      params:

Where `template` is text content containing 0 or more things to be
replaced, and `params` is a list of tokens to search for and replace
in the `template`.

We use `str_replace` to substitute the token `$WAIT_HANDLE` with the
result of calling `get_resource` on our `docker_wait_handle` resource.
This results in a URL that contains an EC2-style signed URL that will
deliver the necessary notification to Heat.  In this example we're
using the `cfn-signal` tool, which is included in the Fedora cloud
images, but you could accomplish the same thing with `curl`:

    curl -X PUT -H 'Content-Type: application/json' \
      --data-binary '{"Status": "SUCCESS",
        "Reason": "Setup complete",
        "Data": "OK", "UniqueId": "00000"}' \
      "$WAIT_HANDLE"

You need to have correctly configured Heat in order for this to work;
I've written a short [companion article][waithelp] that contains a checklist
and pointers to additional documentation to help work around some
common issues.

[waithelp]: {{< ref "using-wait-conditions-with-hea" >}}

## Templates: Defining Docker containers

**UPDATE**: I have generated some [annotated documentation for the
Docker plugin][dockerdoc].

[dockerdoc]: {{< ref "docker-contain-doc" >}}

Now that we have arranged for Heat to wait for the server to finish
configuration before starting Docker contains, how do we create a
container?  As Scott Lowe noticed in his [blog post about Heat and
Docker][scott], there is very little documentation available out there
for the Docker plugin (something I am trying to remedy with this blog
post!).  Things are not quite as bleak as you might think, because
Heat resources are to a certain extent self-documenting.  If you run:

[scott]: http://blog.scottlowe.org/2014/08/22/a-heat-template-for-docker-containers/

    $ heat resource-template DockerInc::Docker::Container

You will get a complete description of the attributes and properties
available in the named resource.  The `parameters` section is probably
the most descriptive:

    parameters:
      cmd:
        Default: []
        Description: Command to run after spawning the container.
        Type: CommaDelimitedList
      dns: {Description: Set custom dns servers., Type: CommaDelimitedList}
      docker_endpoint: {Description: Docker daemon endpoint (by default the local docker
          daemon will be used)., Type: String}
      env: {Description: Set environment variables., Type: CommaDelimitedList}
      hostname: {Default: '', Description: Hostname of the container., Type: String}
      image: {Description: Image name., Type: String}
      links: {Description: Links to other containers., Type: Json}
      memory: {Default: 0, Description: Memory limit (Bytes)., Type: Number}
      name: {Description: Name of the container., Type: String}
      open_stdin:
        AllowedValues: ['True', 'true', 'False', 'false']
        Default: false
        Description: Open stdin.
        Type: String
      port_bindings: {Description: TCP/UDP ports bindings., Type: Json}
      port_specs: {Description: TCP/UDP ports mapping., Type: CommaDelimitedList}
      privileged:
        AllowedValues: ['True', 'true', 'False', 'false']
        Default: false
        Description: Enable extended privileges.
        Type: String
      stdin_once:
        AllowedValues: ['True', 'true', 'False', 'false']
        Default: false
        Description: If true, close stdin after the 1 attached client disconnects.
        Type: String
      tty:
        AllowedValues: ['True', 'true', 'False', 'false']
        Default: false
        Description: Allocate a pseudo-tty.
        Type: String
      user: {Default: '', Description: Username or UID., Type: String}
      volumes:
        Default: {}
        Description: Create a bind mount.
        Type: Json
      volumes_from: {Default: '', Description: Mount all specified volumes., Type: String}

The `port_specs` and `port_bindings` parameters require a little
additional explanation.

The `port_specs` parameter is a list of (TCP) ports that will be
"exposed" by the container (similar to the `EXPOSE` directive in a
Dockerfile).  This corresponds to the `PortSpecs` argument in the the
[/containers/create][api-create] call of the [Docker remote API][].
For example:

[docker remote api]: https://docs.docker.com/reference/api/docker_remote_api/
[api-create]: https://docs.docker.com/reference/api/docker_remote_api_v1.14/#create-a-container

    port_specs:
      - 3306
      - 53/udp
    
The `port_bindings` parameter is a mapping that allows you to bind
host ports to ports in the container, similar to the `-p` argument to
`docker run`.  This corresponds to the
[/containers/(id)/start][api-start] call in the [Docker remote API][].
In the mappings, the key (left-hand side) is the *container* port, and
the value (right-hand side) is the *host* port.

[api-start]: https://docs.docker.com/reference/api/docker_remote_api_v1.14/#start-a-container

For example, to bind container port 3306 to host port 3306:

    port_bindings:
      3306: 3306

To bind port 9090 in a container to port 80 on the host:

    port_bindings:
      9090: 80

And in theory, this should also work for UDP ports (but in practice
there is an issue between the Docker plugin and the `docker-py` Python
module which makes it impossible to expose UDP ports via `port_specs`;
this is fixed in {{< pull-request "docker/docker-py/310" >}} on GitHub).

    port_bindings:
      53/udp: 5300

With all of this in mind, we can create a container resource
definition:

    docker_dbserver:
      type: "DockerInc::Docker::Container"

      # here's where we set the dependency on the WaitCondition
      # resource we mentioned earlier.
      depends_on:
        - docker_wait_condition

      properties:
        docker_endpoint:
          str_replace:
            template: "tcp://$HOST:2375"
            params:
              "$HOST":
                get_attr:
                  - docker_server_floating
                  - floating_ip_address
        image: mysql
        env: 
          # The official MySQL docker image expect the database root
          # password to be provided in the MYSQL_ROOT_PASSWORD
          # environment variable.
          - str_replace:
              template: MYSQL_ROOT_PASSWORD=$PASSWORD
              params:
                "$PASSWORD":
                  get_param:
                    mysql_root_password
        port_specs:
          - 3306
        port_bindings:
          3306: 3306

Take a close look at how we're setting the `docker_endpoint` property:

    docker_endpoint:
      str_replace:
        template: "tcp://$HOST:2375"
        params:
          "$HOST":
            get_attr:
              - docker_server_floating
              - floating_ip_address

This uses the `get_attr` function to get the `floating_ip_address`
attribute from the `docker_server_floating` resource, which you can
find in the [complete template][].  We take the return value from that
function and use `str_replace` to substitute that into the
`docker_endpoint` URL.

## The pudding

Using the [complete template][] with an appropriate local environment
file, I can launch this stack by runnign:

    $ heat stack-create -f docker-server.yml -e local.env docker

And after a while, I can run 

    $ heat stack-list

And see that the stack has been created successfully:

    +--------------------------------------+------------+-----------------+----------------------+
    | id                                   | stack_name | stack_status    | creation_time        |
    +--------------------------------------+------------+-----------------+----------------------+
    | c0fd793e-a1f7-4b35-afa9-12ba1005925a | docker     | CREATE_COMPLETE | 2014-08-31T03:01:14Z |
    +--------------------------------------+------------+-----------------+----------------------+

And I can ask for status information on the individual resources in
the stack:

    $ heat resource-list docker
    +------------------------+------------------------------------------+-----------------+
    | resource_name          | resource_type                            | resource_status |
    +------------------------+------------------------------------------+-----------------+
    | fixed_network          | OS::Neutron::Net                         | CREATE_COMPLETE |
    | secgroup_db            | OS::Neutron::SecurityGroup               | CREATE_COMPLETE |
    | secgroup_docker        | OS::Neutron::SecurityGroup               | CREATE_COMPLETE |
    | secgroup_webserver     | OS::Neutron::SecurityGroup               | CREATE_COMPLETE |
    | docker_wait_handle     | AWS::CloudFormation::WaitConditionHandle | CREATE_COMPLETE |
    | extrouter              | OS::Neutron::Router                      | CREATE_COMPLETE |
    | fixed_subnet           | OS::Neutron::Subnet                      | CREATE_COMPLETE |
    | secgroup_common        | OS::Neutron::SecurityGroup               | CREATE_COMPLETE |
    | docker_server_eth0     | OS::Neutron::Port                        | CREATE_COMPLETE |
    | extrouter_inside       | OS::Neutron::RouterInterface             | CREATE_COMPLETE |
    | docker_server          | OS::Nova::Server                         | CREATE_COMPLETE |
    | docker_server_floating | OS::Neutron::FloatingIP                  | CREATE_COMPLETE |
    | docker_wait_condition  | AWS::CloudFormation::WaitCondition       | CREATE_COMPLETE |
    | docker_webserver       | DockerInc::Docker::Container             | CREATE_COMPLETE |
    | docker_dbserver        | DockerInc::Docker::Container             | CREATE_COMPLETE |
    +------------------------+------------------------------------------+-----------------+

I can run `nova list` and see information about my running Nova
server:

    +--------...+-----------------...+------------------------------------------------------------+
    | ID     ...| Name            ...| Networks                                                   |
    +--------...+-----------------...+------------------------------------------------------------+
    | 301c5ec...| docker-docker_se...| docker-fixed_network-whp3fxhohkxk=10.0.0.2, 192.168.200.46 |
    +--------...+-----------------...+------------------------------------------------------------+

I can point a Docker client at the remote address and see the running
containers:

    $ docker-1.2 -H tcp://192.168.200.46:2375 ps
    CONTAINER ID        IMAGE                     COMMAND                CREATED             STATUS              PORTS                    NAMES
    f2388c871b20        mysql:5                   /entrypoint.sh mysql   5 minutes ago       Up 5 minutes        0.0.0.0:3306->3306/tcp   grave_almeida       
    9596cbe51291        larsks/simpleweb:latest   /bin/sh -c '/usr/sbi   11 minutes ago      Up 11 minutes       0.0.0.0:80->80/tcp       hungry_tesla        

And I can point a `mysql` client at the remote address and access the
database server:

    $ mysql -h 192.168.200.46 -u root -psecret mysql
    Reading table information for completion of table and column names
    You can turn off this feature to get a quicker startup with -A
    [...]
    MySQL [mysql]> 

## When things go wrong

Your `heat-engine` log, generally `/var/log/heat/engine.log`, is going
to be your best source of information if things go wrong.  The `heat
stack-show` command will generally provide useful fault information if
your stack ends up in the `CREATE_FAILED` (or `DELETE_FAILED`) state.



