---
categories: [tech]
title: "Directing different ports to different containers with Traefik"
date: "2022-06-20"
tags:
  - containers
  - docker
  - traefik
---

This post is mostly for myself: I find the [Traefik][] documentation hard to navigate, so having figured this out in response to [a question on Stack Overflow][], I'm putting it here to help it stick in my head.

[traefik]: https://traefik.io
[a question on stack overflow]: https://stackoverflow.com/a/72694677/147356

The question asks essentially how to perform port-based routing of requests to containers, so that a request for `http://example.com` goes to one container while a request for `http://example.com:9090` goes to a different container.

## Creating entrypoints

A default Traefik configuration will already have a listener on port 80, but if we want to accept connections on port 9090 we need to create a new listener: what Traefik calls an [entrypoint][]. We do this using the `--entrypoints.<name>.address` option. For example, `--entrypoints.ep1.address=80` creates an entrypoint named `ep1` on port 80, while `--entrypoints.ep2.address=9090` creates an entrypoint  named `ep2` on port 9090. Those names are important because we'll use them for mapping containers to the appropriate listener later on.

[entrypoint]: https://doc.traefik.io/traefik/routing/entrypoints/

This gives us a Traefik configuration that looks something like:

```
  proxy:
    image: traefik:latest
    command:
      - --api.insecure=true
      - --providers.docker
      - --entrypoints.ep1.address=:80
      - --entrypoints.ep2.address=:9090
    ports:
      - "80:80"
      - "127.0.0.1:8080:8080"
      - "9090:9090"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

We need to publish ports `80` and `9090` on the host in order to accept connections. Port 8080 is by default the Traefik dashboard; in this configuration I have it bound to `localhost` because I don't want to provide external access to the dashboard.

## Routing services

Now we need to configure our services so that connections on ports 80 and 9090 will get routed to the appropriate containers. We do this using the `traefik.http.routers.<name>.entrypoints` label. Here's a simple example:

```
app1:
  image: docker.io/alpinelinux/darkhttpd:latest
  labels:
    - traefik.http.routers.app1.entrypoints=ep1
    - traefik.http.routers.app1.rule=Host(`example.com`)
```

In the above configuration, we're using the following labels:

- ``traefik.http.routers.app1.entrypoints=ep1``

  This binds our `app1` container to the `ep1` entrypoint.

- ``traefik.http.routers.app1.rule=Host(`example.com`)``

  This matches requests with `Host: example.com`.

So in combination, these two rules say that any request on port 80 for `Host: example.com` will be routed to the `app1` container.

To get port `9090` routed to a second container, we add:

```
app2:
  image: docker.io/alpinelinux/darkhttpd:latest
  labels:
    - traefik.http.routers.app2.rule=Host(`example.com`)
    - traefik.http.routers.app2.entrypoints=ep2
```

This is the same thing, except we use entrypoint `ep2`.

With everything running, we can watch the logs from `docker-compose up` and see that a request on port 80:

```
curl -H 'host: example.com' localhost
```

Is serviced by `app1`:

```
app1_1   | 172.20.0.2 - - [21/Jun/2022:02:44:11 +0000] "GET / HTTP/1.1" 200 354 "" "curl/7.76.1"
```

And that request on port 9090:

```
curl -H 'host: example.com' localhost:9090
```

Is serviced by `app2`:

```
app2_1   | 172.20.0.2 - - [21/Jun/2022:02:44:39 +0000] "GET / HTTP/1.1" 200 354 "" "curl/7.76.1"
```

---

The complete `docker-compose.yaml` file from this post looks like:

```
version: "3"

services:
  proxy:
    image: traefik:latest
    command:
      - --api.insecure=true
      - --providers.docker
      - --entrypoints.ep1.address=:80
      - --entrypoints.ep2.address=:9090
    ports:
      - "80:80"
      - "8080:8080"
      - "9090:9090"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  app1:
    image: docker.io/alpinelinux/darkhttpd:latest
    labels:
      - traefik.http.routers.app1.rule=Host(`example.com`)
      - traefik.http.routers.app1.entrypoints=ep1

  app2:
    image: docker.io/alpinelinux/darkhttpd:latest
    labels:
      - traefik.http.routers.app2.rule=Host(`example.com`)
      - traefik.http.routers.app2.entrypoints=ep2
```
