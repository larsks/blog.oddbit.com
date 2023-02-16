---
categories:
- tech
date: '2020-09-25'
filename: 2020-09-25-building-multi-architecture-im.md
tags:
- docker
title: Building multi-architecture images with GitHub Actions

---

At work we have a cluster of IBM Power 9 systems running OpenShift. The
problem with this environment is that nobody runs Power 9 on their desktop,
and Docker Hub only offers automatic build support for the x86
architecture. This means there's no convenient options for building Power 9
Docker images...or so I thought.

It turns out that [Docker][] provides [GitHub actions][] that make the process
of producing multi-architecture images quite simple.

[Docker]: https://github.com/docker
[github actions]: https://github.com/features/actions

The code demonstrated in this post can be found in my [hello-flask][]
GitHub repository.

[hello-flask]: https://github.com/larsks/hello-flask

## Configuring secrets

There is some information we need to provide to our workflow that we don't
want to hardcode into configuration files, both for reasons of security (we
don't want to expose passwords in the repository) and convenience (we want
other people to be able to fork this repository and run the workflow
without needing to make any changes to the code).

We can do this by configuring "secrets" in the repository on GitHub. You
can configure secrets by visiting the "Secrets" tab in your repository
settings (`https://github.com/<USERNAME>/<REPOSITORY>/settings/secrets`),

For this workflow, we're going to need two secrets:

- `DOCKER_USERNAME` -- this is our Docker Hub username; we'll need this
  both for authentication and to set the namespace for the images we're
  building.

- `DOCKER_PASSWORD` -- this is our Docker Hub password, used for
  authentication.

Within a workflow, we can refer to these secrets using syntax like `${{
secrets.DOCKER_USERNAME }}` (you'll see example of this later on).

## Creating a workflow

In the repository containing your `Dockerfile`, create a
`.github/workflows` directory. This is where we will place the files that
configure GitHub actions. In this directory, create a file called
`build_images.yml` (the particular name isn't important, but it's nice to
make names descriptive).

We'll first give this workflow a name and configure it to run for pushes on
our `master` branch by adding the following to our `build_images.yml` file:

```
---
name: 'build images'

on:
  push:
    branches:
      - master
```

## Setting up jobs

With that boilerplate out of the way, we can start configuring the jobs
that will comprise our workflow. Jobs are defined in the `jobs` section of
the configuration file, which is a dictionary that maps job names to their
definition. A job can have multiple actions. For this example, we're going
to set up a `docker` job that will perform the following steps:

- check out the repository
- prepare some parameters
- set up qemu, which is used to provide emulated environments for 
  building on architecture other than the host arch
- configure the docker builders
- authenticate to docker hub
- build and push the images to docker hub

We start by providing a name for our job and configuring the machine on
which the jobs will run. In this example, we're using `ubuntu-latest`;
other options include some other Ubuntu variants, Windows, and MacOS (and
you are able to host your own custom builders, but that's outside the scope
of this article).

```
jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
```

### Checking out the repository

In our first step, we use the standard [actions/checkout][]
action to check out the repository:

[actions/checkout]: https://github.com/actions/checkout

```
      - name: Checkout
        uses: actions/checkout@v2
```

### Preparing parameters

The next step is a simple shell script that sets some output parameters we
will be able to consume in subsequent steps. A script can set parameters by
generating output in the form:

```
::set-output name=<name>::<value>
```

In other steps, we can refer to these parameters using the syntax 
`${{ steps.<step_name>.output.<name> }}` (e.g. `${{ steps.prep.output.tags
}}`).

We're going to use this step to set things like the image name (using our
`DOCKER_USERNAME` secret to set the namespace), and to set up several tags
for the image:

- By default, we tag it `latest`
- If we're building from a git tag, use the tag name instead of `latest`.
  Note that here we're assuming that git tags are of the form `v1.0`, so we
  strip off that initial `v` to get a Docker tag that is just the version
  number.
- We also tag the image with the short commit id

```
      - name: Prepare
        id: prep
        run: |
          DOCKER_IMAGE=${{ secrets.DOCKER_USERNAME }}/${GITHUB_REPOSITORY#*/}
          VERSION=latest
          SHORTREF=${GITHUB_SHA::8}

          # If this is git tag, use the tag name as a docker tag
          if [[ $GITHUB_REF == refs/tags/* ]]; then
            VERSION=${GITHUB_REF#refs/tags/v}
          fi
          TAGS="${DOCKER_IMAGE}:${VERSION},${DOCKER_IMAGE}:${SHORTREF}"

          # If the VERSION looks like a version number, assume that
          # this is the most recent version of the image and also
          # tag it 'latest'.
          if [[ $VERSION =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            TAGS="$TAGS,${DOCKER_IMAGE}:latest"
          fi

          # Set output parameters.
          echo ::set-output name=tags::${TAGS}
          echo ::set-output name=docker_image::${DOCKER_IMAGE}
```

### Set up QEMU

The [docker/setup-qemu][] action installs QEMU [static binaries][], which
are used to run builders for architectures other than the host.

[docker/setup-qemu]: https://github.com/docker/setup-qemu-action
[static binaries]: https://wiki.debian.org/QemuUserEmulation

```
      - name: Set up QEMU
        uses: docker/setup-qemu-action@master
        with:
          platforms: all
```

### Set up Docker builders

The [docker/setup-buildx][] action configures [buildx][], which is a Docker
CLI plugin that provides enhanced build capabilities. This is the
infrastructure that the following step will use for actually building
images.

[docker/setup-buildx]: https://github.com/docker/setup-buildx-action
[buildx]: https://github.com/docker/buildx

```
      - name: Set up Docker Buildx
        id: buildx
        uses: docker/setup-buildx-action@master
```

### Authenticate to Docker Hub

In order to push images to Docker Hub, we use the [docker/login-action][]
action to authenticate. This uses the `DOCKER_USERNAME` and
`DOCKER_PASSWORD` secrets we created earlier in order to establish
credentials for use in subsequent steps.

[docker/login-action]: https://github.com/docker/login-action

```
      - name: Login to DockerHub
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v1
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
```

### Build and push the images

This final step uses the [docker/build-push-action][] to build the images
and push them to Docker Hub using the tags we defined in the `prep` step.
In this example, we're building images for `amd64`, `arm64`, and `ppc64le`
architectures.

```
      - name: Build
        uses: docker/build-push-action@v2
        with:
          builder: ${{ steps.buildx.outputs.name }}
          context: .
          file: ./Dockerfile
          platforms: linux/amd64,linux/arm64,linux/ppc64le
          push: true
          tags: ${{ steps.prep.outputs.tags }}
```

## The complete workflow

When we put all of the above together, we get:

```
---
name: 'build images'

on:
  push:
    branches:
      - master

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v2

      - name: Prepare
        id: prep
        run: |
          DOCKER_IMAGE=${{ secrets.DOCKER_USERNAME }}/${GITHUB_REPOSITORY#*/}
          VERSION=latest
          SHORTREF=${GITHUB_SHA::8}

          # If this is git tag, use the tag name as a docker tag
          if [[ $GITHUB_REF == refs/tags/* ]]; then
            VERSION=${GITHUB_REF#refs/tags/v}
          fi
          TAGS="${DOCKER_IMAGE}:${VERSION},${DOCKER_IMAGE}:${SHORTREF}"

          # If the VERSION looks like a version number, assume that
          # this is the most recent version of the image and also
          # tag it 'latest'.
          if [[ $VERSION =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            TAGS="$TAGS,${DOCKER_IMAGE}:latest"
          fi

          # Set output parameters.
          echo ::set-output name=tags::${TAGS}
          echo ::set-output name=docker_image::${DOCKER_IMAGE}

      - name: Set up QEMU
        uses: docker/setup-qemu-action@master
        with:
          platforms: all

      - name: Set up Docker Buildx
        id: buildx
        uses: docker/setup-buildx-action@master

      - name: Login to DockerHub
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v1
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build
        uses: docker/build-push-action@v2
        with:
          builder: ${{ steps.buildx.outputs.name }}
          context: .
          file: ./Dockerfile
          platforms: linux/amd64,linux/arm64,linux/ppc64le
          push: true
          tags: ${{ steps.prep.outputs.tags }}
```

You can grab the [hello-flask][] repository and try this out yourself.
You'll need to set up the secrets described earlier in this article, but
then for each commit to the `master` branch you will end up a new image,
tagged both as `latest` and with the short git commit id.

## The results

We can use the `docker manifest inspect` command to inspect the output of
the build step. In the output below, you can see the images build for our
three target architectures:

```
$ docker manifest inspect !$
docker manifest inspect larsks/hello-flask
{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
   "manifests": [
      {
         "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
         "size": 3261,
         "digest": "sha256:c6bab778a9fd0dc7bf167a5a49281bcd5ebc5e762ceeb06791aff8f0fbd15325",
         "platform": {
            "architecture": "amd64",
            "os": "linux"
         }
      },
      {
         "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
         "size": 3261,
         "digest": "sha256:3c02f36562fcf8718a369a78054750382aba5706e1e9164b76bdc214591024c4",
         "platform": {
            "architecture": "arm64",
            "os": "linux"
         }
      },
      {
         "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
         "size": 3262,
         "digest": "sha256:192fc9acd658edd6b7f2726f921cba2582fb1101d929800dff7fb53de951dd76",
         "platform": {
            "architecture": "ppc64le",
            "os": "linux"
         }
      }
   ]
}
```

## Caveats

This process assumes, of course, that your base image of choice is available for your selected architectures. [According to Docker][]:

> Most of the official images on Docker Hub provide a variety of architectures.
> For example, the busybox image supports amd64, arm32v5, arm32v6, arm32v7,
> arm64v8, i386, ppc64le, and s390x.

So if you are starting from one of the official images, you'll probably be in good shape. On the other hand, if you're attempting to use a community image as a starting point, you might find that it's only available for a single architecture.

[according to docker]: https://docs.docker.com/docker-for-mac/multi-arch/
