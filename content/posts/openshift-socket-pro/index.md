---
categories: [tech]
aliases: ["/2013/11/23/openshift-socket-pro/"]
title: Sockets on OpenShift
date: "2013-11-23"
tags:
  - openshift
  - javascript
---

In this article, a followup to my [previous post][] regarding
long-poll servers and Python, we investigate the code changes that
were necessary to make the code work when deployed on OpenShift.

<!-- more -->

In the previous post, we implemented IO polling to watch for client
disconnects at the same time we were waiting for messages on a message
bus:

    poll = zmq.Poller()
    poll.register(subsock, zmq.POLLIN)
    poll.register(rfile, zmq.POLLIN)

    events = dict(poll.poll())

    .
    .
    .

If you were to try this at home, you would find that everything worked
as described...but if you were to deploy the same code to OpenShift,
you would find that the problem we were trying to solve (the server
holding file descriptors open after a client disconnected) would still
exist.

So, what's going on here?  I spent a chunk of time trying to figure
this out myself.  I finally found [this post][paas-websockets] by
Marak Jelen discussing issues with [websockets][] in OpenShift, which
says, among other things:

> For OpenShift as a PaaS provider, WebSockets were a big challenge.
> The routing layer that sits between the user's browser and your
> application must be able to route and handle WebSockets. OpenShift
> uses Apache as a reverse proxy server and a main component to route
> requests throughout the platform. However, Apache's mod_proxy has
> been problematic with WebSockets, so OpenShift implemented a new
> Node.js based routing layer that provides scalability and the
> possibility to expand features provided to our users.

In order to work around these problems, an alternate [Node.js][] based
front-end has been deployed on port 8000.  So if your application is
normally available at `http://myapplication-myname.rhcloud.com`, you
can also access it at `http://myapplication-myname.rhcloud.com:8000`.

Not unexpectedly, it seems that the same things that can cause
difficulties with WebSockets connections can also interfere with the
operation of a long-poll server.  The root of the problem is that your
service running on OpenShift never receives notifications of client
disconnects.  You can see this by opening up a connection to your
service.  Assuming that you've deployed the [pubsub example][], you
can run something like this:

    $ curl http://myapplication-myname.rhcloud.com/sub

Leave the connection open and [log in to your OpenShift
instance][login].  Run `netstat` to see the existing connection:

    $ netstat -tan |
      grep $OPENSHIFT_PYTHON_IP |
      grep $OPENSHIFT_PYTHON_PORT |
      grep ESTABLISHED
    tcp        0      0 127.6.26.1:15368            127.6.26.1:8080             ESTABLISHED 
    tcp        0      0 127.6.26.1:8080             127.6.26.1:15368            ESTABLISHED 

Now close your client, and re-run the `netstat` command on your
OpenShift instance.  You will find that the client connection  from
the front-end proxies to your server is still active.  Because the
server never receives any notification that the client has closed the
connection, no amount of `select` or `poll` or anything else will
solve this problem.

Now, try the same experiment using port 8000.  That is, run:

    $ curl http://myapplication-myname.rhcloud.com:8000/sub

Verify that when you close your client, the connection is long evident
in your server.  This means that we need to modify our JavaScript code
to poll using port 8000, which is why in [pubsub.js][] you will find
the following:

    if (using_openshift) {
            poll_url = location.protocol + "//" + location.hostname + ":8000/sub";
    } else {
            poll_url = "/sub";
    }

## But wait, there's more!

If you were to deploy the above code with no other changes, you would
find a mysterious problem: even though your JavaScript console would
show that your code was successfully polling the server, your client
would never update.  This is because by introducing an alternate port
number to the poll operation you are now running afoul of your
brower's [same origin policy][], a security policy that restricts
JavaScript in your browser from interacting with sites other than the
one from which the script was loaded.

The [CORS][] standard introduces a mechanism to work around this
restriction.  An HTTP response can contain additional access control
headers that instruct your browser to permit access to the resource from
a select set of other origins.  The header is called
`Access-Control-Alliow-Origin`, and you will find it in the [pubsub
example][] in [pubsub.py][]:

        if using_openshift:
            bottle.response.headers['Access-Control-Allow-Origin'] = '*'

With this header in place, your JavaScript can poll your
OpenShift-hosted application on port 8000 and everything will work as
expected...

...barring bugs in my code, which, if discovered, should be reported
[here][issues].

[pubsub example]: https://github.com/larsks/pubsub_example/
[pubsub.js]: https://github.com/larsks/pubsub_example/blob/master/static/pubsub.js
[pubsub.py]: https://github.com/larsks/pubsub_example/blob/master/pubsub.py
[openshift]: http://www.openshift.com/
[paas-websockets]: https://www.openshift.com/blogs/paas-websockets
[websockets]: http://en.wikipedia.org/wiki/WebSocket
[login]: https://www.openshift.com/developers/remote-access
[same origin policy]: http://en.wikipedia.org/wiki/Same-origin_policy
[cors]: http://en.wikipedia.org/wiki/Cross-origin_resource_sharing
[issues]: https://github.com/larsks/pubsub_example/issues
[node.js]: http://nodejs.org/
[previous post]: {{< ref "long-polling-with-ja" >}}

