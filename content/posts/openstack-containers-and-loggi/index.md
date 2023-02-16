---
aliases:
- /2017/06/14/openstack-containers-and-logging/
- /post/2017-06-14-openstack-containers-and-logging
categories:
- tech
date: '2017-06-14'
tags:
- openstack
- logging
title: OpenStack, Containers, and Logging
---

I've been thinking about logging in the context of OpenStack and containerized service deployments.  I'd like to lay out some of my thoughts on this topic and see if people think I am talking crazy or not.

There are effectively three different mechanisms that an application can use to emit log messages:

- Via some logging-specific API, such as the legacy syslog API
- By writing a byte stream to stdout/stderr
- By writing a byte stream to a file

A substantial advantage to the first mechanism (using a logging API) is that the application is logging *messages* rather than *bytes*.  This means that if you log a message containing embedded newlines (e.g., python or java tracebacks), you can collect that as a single message rather than having to impose some sort of structure on the byte stream after the fact in order to reconstruct those message.

Another advantage to the use of a logging API is that whatever is receiving logs from your application may be able to annotate the message in various interesting ways.

## Requirements

We're probably going to need to support all three of the above mechanisms.  Some applications (such as `haproxy`) will only log to syslog.  Others may only log to files (such as `mariadb`), and still others may only log to stdout.

## Comparing different log mechanisms

### Logging via syslog

In RHEL, the `journald` process is what listens to `/dev/log`.  If you bind mount journald's `/dev/log` inside a container and then run the following Python code inside that container...

    import logging
    import logging.handlers

    handler = logging.handlers.SysLogHandler(address='/dev/log')
    log = logging.getLogger(__name__)
    log.setLevel('DEBUG')
    log.addHandler(handler)

    log.warning('This is a test')

...you will find that your simple log message has been annotated with
a variety of useful metadata (the output below is the result of
running `journalctl -o verbose ...`):

    Wed 2017-06-14 12:35:57.577061 EDT [s=dc1dd9d61cf045e991f265aa17c5af03;i=6eb6e;b=0d9dc78871c34f43a4a6c27f43cf4167;m=a171206ec6;t=551ee258c6492;x=4e3c71faa52ba9d8]
        _BOOT_ID=0d9dc78871c34f43a4a6c27f43cf4167
        _MACHINE_ID=229916fba5b54252ad4d08efbc581213
        _HOSTNAME=lkellogg-pc0dzzve
        _UID=0
        _GID=0
        _SYSTEMD_SLICE=-.slice
        _TRANSPORT=syslog
        PRIORITY=4
        SYSLOG_FACILITY=1
        _EXE=/usr/bin/python3.5
        _CAP_EFFECTIVE=a80425fb
        _SELINUX_CONTEXT=system_u:system_r:unconfined_service_t:s0
        _COMM=python3
        MESSAGE=This is a test
        _PID=13849
        _CMDLINE=python3 logtest.py
        _SYSTEMD_CGROUP=/docker/7ed1e97d5bb4076caf99393ae3f88b07102a26b0ade2176ed07890bee9a84d24
        _SOURCE_REALTIME_TIMESTAMP=1497458157577061

There are several items of interest there:

- A high resolution timestamp
- The kernel cgroup, which corresponds to the docker container id and thus uniquely identifies the container that originated the message
- The executable path inside the container that generated the message
- The machine id, which uniquely identifies the host

By logging via syslog you have removed the necessity of either (a) handling log rotation in your application or (b) handling log rotation in your container or (c) having to communicate log rotation configuration from the container to the host.  Additionally, you can rely on journald to take care of rate limiting and log size management to prevent a broken application from performing a local DOS of the server.

### Logging via stdout/stderr

Applications that write a byte stream to stdout/stderr will have their output handled by the Docker log driver.  If we run Docker with the `journald` log driver (using the `--log-driver=journald` option to the Docker server), then Docker will add metadata lines read from stdout/stderr.  For example, if we run...

    docker run fedora echo This is a test.

...then our journal will contain:

    Wed 2017-06-14 12:46:45.511515 EDT [s=dc1dd9d61cf045e991f265aa17c5af03;i=6ee72;b=0d9dc78871c34f43a4a6c27f43cf4167;m=a197bf222b;t=551ee4c2b17f7;x=e7c1a220c93ef3cf]
        _BOOT_ID=0d9dc78871c34f43a4a6c27f43cf4167
        _MACHINE_ID=229916fba5b54252ad4d08efbc581213
        _HOSTNAME=lkellogg-pc0dzzve
        PRIORITY=6
        _TRANSPORT=journal
        _UID=0
        _GID=0
        _CAP_EFFECTIVE=3fffffffff
        _SYSTEMD_SLICE=system.slice
        _SELINUX_CONTEXT=system_u:system_r:unconfined_service_t:s0
        _COMM=dockerd
        _EXE=/usr/bin/dockerd
        _SYSTEMD_CGROUP=/system.slice/docker.service
        _SYSTEMD_UNIT=docker.service
        _PID=14309
        _CMDLINE=/usr/bin/dockerd -G docker --dns 172.23.254.1 --log-driver journald -s overlay2
        MESSAGE=This is a test.
        CONTAINER_NAME=happy_euclid
        CONTAINER_TAG=82b87e8902e8
        CONTAINER_ID=82b87e8902e8
        CONTAINER_ID_FULL=82b87e8902e8ac36f3365012ef10c66444fbb8c00e8cec7d7c2a14c05b054127

Like the messages logged via syslog, this also containers information that identifies the source container.  It does not identify the particular binary responsible for emitting the message.

### Logging to a file

When logging to a file, the system is unable to add any metadata for us automatically.  We can derive similar information by logging to a container-specific location (`/var/log/CONTAINERNAME/...`, for example), or by configuring our application to include specific information in the log messages, but ultimately this is the least information-rich mechanism available to us.  Furthermore, it necessitates that we configure some sort of container-aware log rotation strategy to avoid eating up all the available disk space over time.

## Log collection

Our goal is not simply to make log messages available locally.  In
general, we also want to aggregate log messages from several machines
into a single location where we can perform various sorts of queries,
analysis, and visualization.  There are a number of solutions in place
for getting logs off a local server to a central collector, including both [fluentd][] and [rsyslog][].

[rsyslog]: http://www.rsyslog.com/
[fluentd]: http://www.fluentd.org/

In the context of the above discussion, it turns out that `rsyslog` has some very desirable features.  In particular, the [imjournal][] input module has support for reading structured messages from journald and exporting those to a remote collector (such as [ElasticSearch][]) with their structure intact.  Fluentd does not ship with journald support as a core plugin.

[ElasticSearch]: https://www.elastic.co/
[imjournal]: http://www.rsyslog.com/doc/v8-stable/configuration/modules/imjournal.html
[imfile]: http://www.rsyslog.com/doc/v8-stable/configuration/modules/imfile.html

Rsyslog version 8.x and later have a rich language for filtering, annotating, and otherwise modifying log messages that would allow us to do things such as add host-specific tags to messages, normalize log messages from applications with poorly designed log messages, and perform other transformations before sending them on to a remote collector.

For example, we would ensure that messages from containerized services logged via syslog *or* via stdout/stderr have a `CONTAINER_ID_FULL` field with something like the following:

    if re_match($!_SYSTEMD_CGROUP, "^/docker/") then {
            set $!CONTAINER_ID_FULL = re_extract($!_SYSTEMD_CGROUP, "^/docker/(.*)", 0, 1, "unknown");
    }

This matches the `_SYSTEMD_CGROUP` field of the message, extracts the container id, and uses that to set the `CONTAINER_ID_FULL` property on the message.

## Recommendations

1. Provide a consistent logging environment to containerized services.  Provide every container both with `/dev/log` and a container-specific host directory mounted on `/var/log`.
2. For applications that support logging to syslog (such as all consumers of `oslo.log`), configure them to log exclusively via syslog.
3.  For applications that are unable to log via syslog but are able to log to stdout/stderr, ensure that Docker is using the `journald` log driver.
4. For applications that can only log to files, configure rsyslog on the host to read those files using the [imfile][] input plugin.
5. Use rsyslog on the host to forward structured messages to a remote collector.