---
categories: [tech]
aliases: ["/2014/01/14/direct-access-to-nova-metadata/"]
title: Direct access to Nova metadata
date: "2014-01-14"
tags:
- openstack
---

When you boot a virtual instance under [OpenStack][], your instance
has access to certain [instance metadata][] via the Nova metadata service,
which is canonically available at <http://169.254.169.254/>.

In an environment running [Neutron][], a request from your instance
must traverse a number of steps:

- From the instance to a router,
- Through a NAT rule in the router namespace, 
- To an instance of the neutron-ns-metadata-proxy,
- To the actual Nova metadata service

When there are problem accessing the metadata, it can be helpful to
verify that the metadata service itself is configured correctly and
returning meaningful information.

<!-- more -->

Naively trying to contact the Nova metadata service listening on port
8775 will, not unexpectedly, fail:

    $ curl http://localhost:8775/latest/meta-data/
    <html>
     <head>
      <title>400 Bad Request</title>
     </head>
     <body>
      <h1>400 Bad Request</h1>
      X-Instance-ID header is missing from request.<br /><br />
     </body>

You can grab the UUID of a running instance with `nova list`:

    $ nova list
    +--------------------------------------+-------...
    | ID                                   | Name  ...
    +--------------------------------------+-------...
    | 32d0524b-314d-4594-b3a3-607e3f2354f8 | test0 ...
    +--------------------------------------+-------...

You can retry your request with an appropraite `X-Instance-ID` header
(`-H 'x-instance-id: 32d0524b-314d-4594-b3a3-607e3f2354f8'`), but
ultimately (after also adding the tenant id), you'll find that you
need to add an `x-instance-id-signature` header.  If you investigate
the [Nova source code][], you'll find that this header is calculated
via an HMAC over the instance ID and a shared secret:

    expected_signature = hmac.new(
        CONF.neutron_metadata_proxy_shared_secret,
        instance_id,
        hashlib.sha256).hexdigest()

You can get the shared secret from `/etc/nova/nova.conf`:

    # grep shared_secret /etc/nova/nova.conf
    neutron_metadata_proxy_shared_secret=deadbeef2eb84d8d

And insert that into the previous Python code:

    Python 2.7.5 (default, Nov 12 2013, 16:18:42) 
    [GCC 4.8.2 20131017 (Red Hat 4.8.2-1)] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import hmac
    >>> import hashlib
    >>> hmac.new('deadbeef2eb84d8d',
    >>> '32d0524b-314d-4594-b3a3-607e3f2354f8',
    >>> hashlib.sha256).hexdigest()
    '6bcbe3885ae7efc49cef35b438efe29c95501f4a720a0c53ed000d8fcf04a605'
    >>> 

And now make a request directly to the metadata service:

    $ curl \
      -H 'x-instance-id: 32d0524b-314d-4594-b3a3-607e3f2354f8' \
      -H 'x-tenant-id: 28a490a0f8b28800181ce490a74df8d2' \
      -H 'x-instance-id-signature: 6bcbe3885ae7efc49cef35b438efe29c95501f4a720a0c53ed000d8fcf04a605' \
      http://localhost:8775/latest/meta-data
    ami-id
    ami-launch-index
    ami-manifest-path
    block-device-mapping/
    hostname
    instance-action
    instance-id
    instance-type
    kernel-id
    local-hostname
    local-ipv4
    placement/
    public-hostname
    public-ipv4
    public-keys/
    ramdisk-id
    reservation-id

And you're done!

[nova source code]: https://github.com/openstack/nova/blob/master/nova/api/metadata/handler.py
[openstack]: http://www.openstack.org/
[instance metadata]: http://docs.openstack.org/admin-guide-cloud/content//section_metadata-service.html
[neutron]: https://wiki.openstack.org/wiki/Neutron

