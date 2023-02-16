---
categories:
- tech
date: '2021-02-08'
draft: false
filename: 2021-02-08-remediating-poor-pypi-performa.md
stub: remediating-poor-pypi-performa
tags:
- python
- pypi
- podman
title: Remediating poor PyPi performance with DevPi

---

Performance of the primary PyPi service has been so bad lately that
it's become very disruptive. Tasks that used to take a few seconds
will now churn along for 15-20 minutes or longer before completing,
which is incredibly frustrating.

I first went looking to see if there was a PyPi mirror infrastructure,
like we see with [CPAN][] for Perl or [CTAN][] for Tex (and similarly
for most Linux distributions).  There is apparently no such beast,

[cpan]: https://www.cpan.org/
[ctan]: https://ctan.org/

I didn't really want to set up a PyPi mirror locally, since the number
of packages I actually use is small vs. the number of packages
available. I figured there must be some sort of caching proxy
available that would act as a shim between me and PyPi, fetching
packages from PyPi and caching them if they weren't already available
locally.

I was previously aware of [Artifactory][], which I suspected (and
confirmed) was capable of this, but while looking around I came across
[DevPi][], which unlike Artifactory is written exclusively for
managing Python packages. DevPi itself is hosted on PyPi, and the
documentation made things look easy to configure.

[artifactory]: https://www.jfrog.com/confluence/display/JFROG/PyPI+Repositories
[devpi]: https://www.devpi.net/

After reading through their [Quickstart: running a pypi mirror on your
laptop][qs] documentation, I built a containerized service that would
be easy for me to run on my desktop, laptop, work computer, etc. You
can find the complete configuration at
https://github.com/oddbit-dot-com/docker-devpi-server.

[qs]: https://devpi.net/docs/devpi/devpi/stable/+doc/quickstart-pypimirror.html

I started with the following `Dockerfile` (note I'm using
[podman][] rather than Docker as my container runtime, but the
resulting image will work fine for either environment):

[podman]: https://podman.io/

```
FROM python:3.9

RUN pip install devpi-server devpi-web
WORKDIR /root
VOLUME /root/.devpi
COPY docker-entrypoint.sh /docker-entrypoint.sh
ENTRYPOINT ["sh", "/docker-entrypoint.sh"]
CMD ["devpi-server", "--host", "0.0.0.0"]
```

This installs both `devpi-server`, which provides the basic caching
for `pip install`, as well as `devpi-web`, which provides support for
`pip search`.

To ensure that things are initialized correctly when the container
start up, I've set the `ENYTRYPOINT` to the following script:

```
#!/bin/sh

if ! [ -f /root/.devpi/server ]; then
	devpi-init
fi

exec "$@"
```

This will run `devpi-init` if the target directory hasn't already been
initialized.

The repository includes a [GitHub workflow][] that builds a new image on each commit
and pushes the result to the `oddbit/devpi-server` repository on
Docker Hub.

[github workflow]: https://github.com/oddbit-dot-com/docker-devpi-server/blob/master/.github/workflows/build_docker_image.yml

Once the image was available on Docker Hub, I created the following
systemd unit to run the service locally:


```
[Service]
Restart=on-failure
ExecStartPre=/usr/bin/rm -f %t/%n-pid
ExecStart=/usr/bin/podman run --replace \
	--conmon-pidfile %t/%n-pid --cgroups=no-conmon \
	--name %n -d -p 127.0.0.1:3141:3141 \
	-v devpi:/root/.devpi oddbit/devpi-server
ExecStopPost=/usr/bin/rm -f %t/%n-pid
PIDFile=%t/%n-pid
Type=forking

[Install]
WantedBy=multi-user.target default.target
```

There are a couple items of note in this unitfile:

- The service is exposed only on `localhost` using `-p
  127.0.0.1:3141:3141`. I don't want this service exposed on
  externally visible addresses since I haven't bothered setting up any
  sort of authentication.

- The service mounts a named volume for use by `devpi-server` via the
  `-v devpi:/root/.devpi` command line option.

This unit file gets installed into
`~/.config/systemd/user/devpi.service`.  Running `systemctl --user
enable --now devpi.service` both enables the service to start at boot
and actually starts it up immediately.

With the service running, the last thing to do is configure `pip` to
utilize it. The following configuration, placed in
`~/.config/pip/pip.conf`, does the trick:


```
[install]
index-url = http://localhost:3141/root/pypi/+simple/

[search]
index = http://localhost:3141/root/pypi/
```

Now both `pip install` and `pip search` hit the local cache instead of
the upstream PyPi server, and things are generally much, much faster.

## For Poetry Users

[Poetry][] respects the `pip` configuration and will Just Work.

[poetry]: https://python-poetry.org/

## For Pipenv Users

[Pipenv][] does not respect the pip configuration [[1][nopip1],
[2][nopip2]], so you will
need to set the `PIPENV_PYPI_MIRROR` environment variable. E.g:

```
export PIPENV_PYPI_MIRROR=http://localhost:3141/root/pypi/+simple/
```

[pipenv]: https://github.com/pypa/pipenv
[nopip1]: https://github.com/pypa/pipenv/issues/1451
[nopip2]: https://github.com/pypa/pipenv/issues/2075
