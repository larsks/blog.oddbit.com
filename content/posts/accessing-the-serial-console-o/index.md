---
aliases:
- /2014/12/22/accessing-the-serial-console-of-your-nova-servers/
- /post/2014-12-22-accessing-the-serial-console-of-your-nova-servers
categories:
- tech
date: '2014-12-22'
tags:
- openstack
- nova
title: Accessing the serial console of your Nova servers
---

One of the new features available in the Juno release of OpenStack is
support for [serial console access to your Nova
servers][serial-ports].  This post looks into how to configure the
serial console feature and then how to access the serial consoles of
your Nova servers.

[serial-ports]: https://blueprints.launchpad.net/nova/+spec/serial-ports

<!-- more -->

## Configuring serial console support

In previous release of OpenStack, read-only access to the serial
console of your servers was available through the
`os-getConsoleOutput` server action (exposed via `nova console-log` on
the command line).  Most cloud-specific Linux images are configured
with a command line that includes something like `console=tty0
console=ttyS0,115200n81`, which ensures that kernel output and other
messages are available on the serial console.  This is a useful
mechanism for diagnosing problems in the event that you do not have
network access to a server.

In Juno, you can exchange this read-only view of the console for
read-write access by setting `enabled=true` in the `[serial_console]`
section of your `nova.conf` file:

    [serial_console]
    enabled=true

This enables the new `os-getSerialConsole` server action.

Much like the configuration for graphical console access, you will also
probably need to provide values for `base_url`, `listen`, and
`proxyclient_address`:

    [serial_console]
    enabled=true

    # Location of serial console proxy. (string value)
    base_url=ws://127.0.0.1:6083/

    # IP address on which instance serial console should listen
    # (string value)
    listen=127.0.0.1

    # The address to which proxy clients (like nova-serialproxy)
    # should connect (string value)
    proxyclient_address=127.0.0.1

The `base_url` setting is what gets passed to clients, so this will
probably be the address of one of your "front-end" controllers (e.g.,
wherever you are running other public APIs or services like Horizon).

The `listen` address is used by `nova-compute` to control on which
address the virtual console will listen (this can be set to `0.0.0.0`
to listen on all available addresses).  The `proxyclient_address`
controls to which address the `nova-serialproxy` service will connect.

In other words: a remote client request a serial console will receive
a websocket URL prefixed by `base_url`.  This URL will connect the
client to the `nova-serialproxy` service.  The `nova-serialproxy`
service will look up the `proxyclient_address` associated with the
requested server, and will connect to the appropriate port at that
address.

Enabling serial console support will result in an entry similar to the
following in the XML description of libvirt guests started by Nova:

    <console type='tcp'>
      <source mode='bind' host='127.0.0.1' service='10000'/>
      <protocol type='raw'/>
      <target type='serial' port='0'/>
      <alias name='serial0'/>
    </console>

## Accessing the serial console

You can use the `nova get-serial-proxy` command to retrieve the
websocket URL for a server's serial console, like this:

    $ nova get-serial-console my-server
    +--------+-----------------------------------------------------------------+
    | Type   | Url                                                             |
    +--------+-----------------------------------------------------------------+
    | serial | ws://127.0.0.1:6083/?token=18510769-71ad-4e5a-8348-4218b5613b3d |
    +--------+-----------------------------------------------------------------+

Or through the REST API like this:

    curl -i 'http://127.0.0.1:8774/v2/<tenant_uuid>/servers/<server_uuid>/action' \
      -X POST \
      -H "Accept: application/json" \
      -H "Content-Type: application/json" \
      -H "X-Auth-Project-Id: <project_id>" \
      -H "X-Auth-Token: <auth_token>" \
      -d '{"os-getSerialConsole": {"type": "serial"}}'

But now that you have a websocket URL, what do you do with it?  It
turns out that there aren't all that many out-of-the-box tools that
will let you connect interactively to this URL from the command line.
While I'm sure that a future version of Horizon will provide a
web-accessible console access mechanism, it is often convenient to
have a command-line tool for this sort of thing because that permits
you to log or otherwise process the output.

Fortunately, it's not too difficult to write a simple client.  The
Python `websocket-client` module has the necessary support; given the
above URL, you can open a connection like this:

    import websocket

    ws = websocket.create_connection(
          'ws://127.0.0.1:6083/?token=18510769-71ad-4e5a-8348-4218b5613b3d',
          subprotocols=['binary', 'base64'])

This gets you a `WebSocket` object with `.send` and `.recv` methods
for sending and receiving data (and a `.fileno` method for use in
event loops).

## I was told there would be no programming

If you don't feel like writing your own websocket client, have no
fear! I have put together a simple client called [novaconsole][].
Assuming that you have valid credentials in your environment, you can
provide it with a server name or UUID:

[novaconsole]: http://github.com/larsks/novaconsole/

    $ novaconsole my-server

You can also provide a verbatim websocket URL (in which case you don't
need to bother with OpenStack authentication):

    $ novaconsole --url ws://127.0.0.1:6083/?token=18510769-71ad-4e5a-8348-4218b5613b3d

In either case, you will have an interactive session to the specified
serial console.  You can exit the session by typing `~.` at the
beginning of a line.

You can only have a single active console connection at a time.  Other
connections will block until you disconnect from the active session.

## But everything is not roses and sunshine

One disadvantage to the serial console support is that it *replaces*
the console log available via `nova console-log`.  This means that if,
for example, a server were to encounter problems configuring
networking and emit errors on the console, you would not be able to
see this information unless you happened to be connected to the
console at the time the errors were generated.

It would be nice to have both mechanisms available -- serial console
support for interactive access, and console logs for retroactive
debugging.