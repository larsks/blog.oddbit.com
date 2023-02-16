---
categories: [tech]
aliases: ["/2019/02/24/docker-build-learns-about-secr/"]
title: "Docker build learns about secrets and ssh agent forwarding"
date: "2019-02-24"
tags:
- "docker"
- "secrets"
---

A common problem for folks working with Docker is accessing resources which require authentication during the image build step.  A particularly common use case is getting access to private git repositories using ssh key-based authentication.  Until recently there hasn't been a great solution:

- you can embed secrets in your image, but now you can't share the image with anybody.
- you can use build arguments, but this requires passing in an unenecrypted private key on the `docker build` command line, which is suboptimal for a number of reasons
- you can perform all the steps requiring authentication at runtime, but this can needlessly complicate your container startup process.

With Docker 18.09, there are some experimental features available that makes this much easier.  You can read the official announcement [here](https://docs.docker.com/develop/develop-images/build_enhancements/), but I wanted to highlight the support for ssh agent forwarding and private keys.

# Prerequisites

In order to use the new features, you first need to explicitly enable BuildKit support by setting `DOCKER_BUILDKIT=1` in your environment:

    export DOCKER_BUILDKIT=1

And to utilize the new `Dockerfile` syntax, you need to start your `Dockerfile` with this directive:

    # syntax=docker/dockerfile:1.0.0-experimental

That instructs Docker to use the named image (`docker/dockerfile:1.0.0-experimental`) to handle the image build process.

## A simple example

The most common use case will probably be forwarding access to your local ssh agent.  In order for the build process to get access to your agent, two things must happen:

1. The `RUN` command that requires credentials must specify `--mount=type=ssh` in order to have access to the forwarded agent connection, and

2. You must pass an appropriate `--ssh` option on the `docker build` command line. This is to prevent a Dockerfile from unexpectedly gaining access to your ssh credentials.

We can see this in action if we start with the following `Dockerfile`:

    # syntax=docker/dockerfile:1.0.0-experimental

    FROM alpine
    RUN apk add --update git openssh

    # This is necessary to prevent the "git clone" operation from failing
    # with an "unknown host key" error.
    RUN mkdir -m 700 /root/.ssh; \
      touch -m 600 /root/.ssh/known_hosts; \
      ssh-keyscan github.com > /root/.ssh/known_hosts

    # This command will have access to the forwarded agent (if one is
    # available)
    RUN --mount=type=ssh git clone git@github.com:moby/buildkit

If we run build the image like this...

    export DOCKER_BUILDKIT=1
    docker build --ssh default -t buildtest .

...then our `git clone` operation will successfully authenticate with github using our ssh private key, assuming that we had one loaded into our local ssh agent.

## But wait, there's more

In the previous example line, the `--ssh default` option requests `docker build` to forward your default ssh agent. There may be situations in which this isn't appropriate (for example, maybe you need to use a key that isn't loaded into your default agent).  You can provide the `--ssh` option with one or more paths to ssh agent sockets or (unencrypted) private key files.  Let's say you have two service-specific private keys:

- For GitHub, you need to use `$HOME/.ssh/github_rsa`
- For BitBucket, you need to use `$HOME/.ssh/bitbucket_rsa`

You can provide the keys on the `docker build` command line like this:

    docker build --ssh github=$HOME/.ssh/github_rsa,bitbucket=$HOME/.ssh/bitbucket_rsa -t buildtest .

Then inside your `Dockerfile`, you can use the `id=<name>` parameter to the `--mount` option to specify which key should be available to the `RUN` command:

    # syntax=docker/dockerfile:1.0.0-experimental

    FROM alpine
    RUN apk add --update git openssh

    # This is necessary to prevent the "git clone" operation from failing
    # with an "unknown host key" error.
    RUN mkdir -m 700 /root/.ssh; \
      touch -m 600 /root/.ssh/known_hosts; \
      ssh-keyscan github.com bitbucket.com > /root/.ssh/known_hosts

    # This command has access to the "github" key
    RUN --mount=type=ssh,id=github git clone git@github.com:some/project

    # This command has access to the "bitbucket" key
    RUN --mount=type=ssh,id=bitbucket git clone git@bitbucket.com:other/project

## Other secrets

In this post I've looked specfically at providing `docker build` with access to your ssh keys.  Docker 18.09 also introduces support for exposing other secrets to the build process; see the official announcement (linked above) for details.
