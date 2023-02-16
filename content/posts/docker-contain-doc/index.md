---
categories: [tech]
aliases: ["/2014/08/31/docker-contain-doc/"]
title: Annotated documentation for DockerInc::Docker::Container
date: "2014-08-30"
tags:
  - docker
  - openstack
  - heat
  - orchestration
---

This is a companion to my [article on the Docker plugin for Heat][1].

[1]: {{< ref "docker-plugin-for-openstack-he" >}}

## DockerInc::Docker::Container

### Properties

- `cmd` : List

    Command to run after spawning the container.

    Optional property.

    Example:

        cmd: [ 'thttpd', '-C', '/etc/thttpd.conf', '-D', '-c', '*.cgi']

- `dns` : List

    Set custom DNS servers.

    Example:

        dns:
          - 8.8.8.8
          - 8.8.4.4

- `docker_endopint` : String

    Docker daemon endpoint.  By default the local Docker daemon will
    be used.

    Example:

        docker_endpoint: tcp://192.168.1.100:2375

- `env` : String

    Set environment variables.

    Example:

        env:
          - MYSQL_ROOT_PASSWORD=secret
          - "ANOTHER_VARIABLE=something long with spaces"

- `hostname` : String

    Hostname of the container.

    Example:

        hostname: mywebserver

- `image` : String

    Image name to boot.

    Example:

        image: mysql

- `links` : Mapping

    Links to other containers.

    Example:

        links:
          name_in_this_container: name_of_that_container

- `memory` : Number

    Memory limit in bytes.

    Example:

        # 512 MB
        memory: 536870912

- `name` : String

    Name of the container.

    Example:

        name: dbserver

- `open_stdin` : Boolean

    True to open `stdin`.

    Example:

        open_stdin: true

- `port_bindings` : Map

    TCP/UDP port bindings.

    Example:

        # bind port 8080 in the container to port 80 on the host
        port_bindings:
          8080: 80

- `port_specs` : List

    List of TCP/UDP ports exposed by the container.

    Example:

        port_specs:
          - 80
          - 53/udp

- `privileged` : Boolean

    Enable extended privileges.

    Example:

        privileged: true

- `stdin_once` : Boolean

    If `true`, close `stdin` after the one attached client disconnects.

    Example:

        stdin_once: true

- `tty` : Boolean

    Allocate a pseudo-tty if `true`.

    Example:

        tty: true

- `user` : String

    Username or UID for running the container.

    Example:

        username: apache

- `volumes` : Map

    Create a bind mount.

    Example:

        volumes:
            /var/tmp/data_on_host: /srv/data_in_container

- `volumes_from` : String

    *This option is broken in the current version of the Docker
    plugin.*

### Attributes

- `info` : Map

    Information about the container.

    Example:

        info:
          value: {get_attr: ["docker_dbserver", "info"]}

    Output:

        {
          "HostsPath": "/var/lib/docker/containers/d6d84d1bbf2984fa3e04cea36c8d10d27d318b6d96b57c41fca2cbc1da23bf71/hosts",
          "Created": "2014-09-01T14:21:02.7577874Z",
          "Image": "a950533b3019d8f6dfdcb8fdc42ef810b930356619b3e4786d4f2acec514238d",
          "Args": [
            "mysqld",
            "--datadir=/var/lib/mysql",
            "--user=mysql"
          ],
          "Driver": "devicemapper",
          "HostConfig": {
            "CapDrop": null,
            "PortBindings": {
              "3306/tcp": [
                {
                  "HostPort": "3306",
                  "HostIp": ""
                }
              ]
            },
            "NetworkMode": "",
            .
            .
            .

- `logs` : String

     Logs from the container.

     Example:

         logs:
           value: {get_attr: ["docker_dbserver", "logs"]}

- `logs_head` : String

     Most recent log line from the container.

     Example:

         logs:
           value: {get_attr: ["docker_dbserver", "logs_head"]}

     Output:

         "2014-09-01 14:21:04 0 [Warning] TIMESTAMP with implicit DEFAULT
         value is deprecated. Please use --explicit_defaults_for_timestamp
         server option (see documentation for more details)."

- `network_gateway` : String

     IP address of the network gateway for the container.

     Example:

         network_gateway:
           value: {get_attr: ["docker_dbserver", "network_gateway"]}

    Output:

        "172.17.42.1"

- `network_info` : Map

     Information about the network configuration of the container.

     Example:

         network_info:
           value: {get_attr: ["docker_dbserver", "network_info"]}

     Output:

         {
           "Bridge": "docker0",
           "TcpPorts": "3306",
           "PortMapping": null,
           "IPPrefixLen": 16,
           "UdpPorts": "",
           "IPAddress": "172.17.0.10",
           "Gateway": "172.17.42.1",
           "Ports": {
             "3306/tcp": [
               {
                 "HostPort": "3306",
                 "HostIp": "0.0.0.0"
               }
             ]
           }
         }

- `network_ip` : String

    IP address assigned to the container.

    Example:

        network_ip:
          value: {get_attr: ["docker_dbserver", "network_ip"]}

    Output:

        "172.17.0.10"

- `network_tcp_ports` : String

    A comma delimited list of TCP ports exposed by the container.

    Example:

        network_tcp_ports:
          value: {get_attr: ["docker_dbserver", "network_tcp_ports"]}

    Output:

        "8443,8080"

- `network_udp_ports` : String

    A comma delimited list of TCP ports exposed by the container.

    Example:

        network_udp_ports:
          value: {get_attr: ["docker_dbserver", "network_udp_ports"]}

    Output:

        "8443,8080"

