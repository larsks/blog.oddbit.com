---
categories: [tech]
title: "Connecting OpenShift to an External Ceph Cluster"
date: "2021-08-23"
tags:
  - ceph
  - openshift
  - ocs
  - odf
  - kubernetes
  - storage
---

Red Hat's [OpenShift Data Foundation][ocs] (formerly "OpenShift
Container Storage", or "OCS") allows you to either (a) automatically
set up a Ceph cluster as an application running on your OpenShift
cluster, or (b) connect your OpenShift cluster to an externally
managed Ceph cluster.  While setting up Ceph as an OpenShift
application is a relatively polished experienced, connecting to an
external cluster still has some rough edges.

[ocs]: https://www.redhat.com/en/technologies/cloud-computing/openshift-data-foundation

**NB** I am not a Ceph expert. If you read this and think I've made a
mistake with respect to permissions or anything else, please feel free
to leave a comment and I will update the article as necessary. In
particular, I think it may be possible to further restrict the `mgr`
permissions shown in this article and I'm interested in feedback on
that topic.

## Installing OCS

Regardless of which option you choose, you start by installing the
"OpenShift Container Storage" operator (the name change apparently
hasn't made it to the Operator Hub yet). When you select "external
mode", you will be given the opportunity to download a Python script
that you are expected to run on your Ceph cluster. This script will
create some Ceph authentication principals and will emit a block of
JSON data that gets pasted into the OpenShift UI to configure the
external StorageCluster resource.

The script has a single required option, `--rbd-data-pool-name`, that
you use to provide the name of an existing pool. If you run the script
with only that option, it will create the following ceph principals
and associated capabilities:

- `client.csi-rbd-provisioner`

  ```
  caps mgr = "allow rw"
  caps mon = "profile rbd"
  caps osd = "profile rbd"
  ```

- `client.csi-rbd-node`

  ```
  caps mon = "profile rbd"
  caps osd = "profile rbd"
  ```

- `client.healthchecker`

  ```
  caps mgr = "allow command config"
  caps mon = "allow r, allow command quorum_status, allow command version"
  caps osd = "allow rwx pool=default.rgw.meta, allow r pool=.rgw.root, allow rw pool=default.rgw.control, allow rx pool=default.rgw.log, allow x pool=default.rgw.buckets.index"
  ```

  This account is used to verify the health of the ceph cluster.

If you also provide the `--cephfs-filesystem-name` option, the script
will also create:

- `client.csi-cephfs-provisioner`

  ```
  caps mgr = "allow rw"
  caps mon = "allow r"
  caps osd = "allow rw tag cephfs metadata=*"
  ```

- `client.csi-cephfs-node`

  ```
  caps mds = "allow rw"
  caps mgr = "allow rw"
  caps mon = "allow r"
  caps osd = "allow rw tag cephfs *=*"
  ```

If you specify `--rgw-endpoint`, the script will create a RGW user
named `rgw-admin-ops-user`with administrative access to the default
RGW pool.

## So what's the problem?

The above principals and permissions are fine if you've created an
external Ceph cluster explicitly for the purpose of supporting a
single OpenShift cluster.

In an environment where a single Ceph cluster is providing storage to
multiple OpenShift clusters, and *especially* in an environment where
administration of the Ceph and OpenShift environments are managed by
different groups, the process, principals, and permissions create a
number of problems.

The first and foremost is that the script provided by OCS both (a)
gathers information about the Ceph environment, and (b) *makes changes
to that environment*. If you are installing OCS on OpenShift and want
to connect to a Ceph cluster over which you do not have administrative
control, you may find yourself stymied when the storage administrators
refuse to run your random Python script on the Ceph cluster.

Ideally, the script would be read-only, and instead of *making*
changes to the Ceph cluster it would only *validate* the cluster
configuration, and inform the administrator of what changes were
necessary. There should be complete documentation that describes the
necessary configuration scripts so that a Ceph cluster can be
configured correctly without running *any* script, and OCS should
provide something more granular than "drop a blob of JSON here" for
providing the necessary configuration to OpenShift.

The second major problem is that while the script creates several
principals, it only allows you to set the name of one of them. The
script has a `--run-as-user` option, which at first sounds promising,
but ultimately is of questionable use: it only allows you set the Ceph
principal used for cluster health checks.

There is no provision in the script to create separate principals for
each OpenShift cluster.

Lastly, the permissions granted to the principals are too broad. For
example, the `csi-rbd-node` principal has access to *all* RBD pools on
the cluster.

## How can we work around it?

If you would like to deploy OCS in an environment where the default
behavior of the configuration script is inappropriate you can work
around this problem by:

- Manually generating the necessary principals (with more appropriate
  permissions), and

- Manually generating the JSON data for input into OCS

### Create the storage

I've adopted the following conventions for naming storage pools and
filesystems:

- All resources are prefixed with the name of the cluster (represented
  here by `${clustername}`).

- The RBD pool is named `${clustername}-rbd`. I create it like this:

  ```
	ceph osd pool create ${clustername}-rbd
	ceph osd pool application enable ${clustername}-rbd rbd
  ```

- The CephFS filesystem (if required) is named
  `${clustername}-fs`, and I create it like this:

  ```
	ceph fs volume create ${clustername}-fs
  ```

  In addition to the filesystem, this creates two pools:

  - `cephfs.${clustername}-fs.meta`
  - `cephfs.${clustername}-fs.data`

### Creating the principals

Assuming that you have followed the same conventions and have an RBD
pool named `${clustername}-rbd` and a CephFS filesystem named
`${clustername}-fs`, the following set of `ceph auth add` commands
should create an appropriate set of principals (with access limited to
just those resources that belong to the named cluster):

```
ceph auth add client.healthchecker-${clustername} \
        mgr "allow command config" \
        mon "allow r, allow command quorum_status, allow command version"

ceph auth add client.csi-rbd-provisioner-${clustername} \
        mgr "allow rw" \
        mon "profile rbd" \
        osd "profile rbd pool=${clustername}-rbd"

ceph auth add client.csi-rbd-node-${clustername} \
        mon "profile rbd" \
        osd "profile rbd pool=${clustername}-rbd"

ceph auth add client.csi-cephfs-provisioner-${clustername} \
        mgr "allow rw" \
        mds "allow rw fsname=${clustername}-fs" \
        mon "allow r fsname=${clustername}-fs" \
        osd "allow rw tag cephfs metadata=${clustername}-fs"

ceph auth add client.csi-cephfs-node-${clustername} \
        mgr "allow rw" \
        mds "allow rw fsname=${clustername}-fs" \
        mon "allow r fsname=${clustername}-fs" \
        osd "allow rw tag cephfs data=${clustername}-fs"
```

Note that I've excluded the RGW permissions here; in our OpenShift
environments, we typically rely on the object storage interface
provided by [Noobaa][] so I haven't spent time investigating
permissions on the RGW side.

[noobaa]: https://www.noobaa.io/

### Create the JSON

The final step is to create the JSON blob that you paste into the OCS
installation UI. I use the following script which calls `ceph -s`,
`ceph mon dump`, and `ceph auth get-key` to get the necessary
information from the cluster:


```
#!/usr/bin/python3

import argparse
import json
import subprocess
from urllib.parse import urlparse

usernames = [
        'healthchecker',
        'csi-rbd-node',
        'csi-rbd-provisioner',
        'csi-cephfs-node',
        'csi-cephfs-provisioner',
        ]


def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument('--use-cephfs', action='store_true', dest='use_cephfs')
    p.add_argument('--no-use-cephfs', action='store_false', dest='use_cephfs')

    p.add_argument('instance_name')

    p.set_defaults(use_rbd=True, use_cephfs=True)

    return p.parse_args()


def main():
    args = parse_args()

    cluster_status = json.loads(subprocess.check_output(['ceph', '-s', '-f', 'json']))
    mon_status = json.loads(subprocess.check_output(['ceph', 'mon', 'dump', '-f', 'json']))

    users = {}
    for username in usernames:
        key = subprocess.check_output(['ceph', 'auth', 'get-key', 'client.{}-{}'.format(username, args.instance_name)])
        users[username] = {
                'name': 'client.{}-{}'.format(username, args.instance_name),
                'key': key.decode(),
                }

    mon_name = mon_status['mons'][0]['name']
    mon_ip = [
            addr for addr in
            mon_status['mons'][0]['public_addrs']['addrvec']
            if addr['type'] == 'v1'
            ][0]['addr']
    prom_url = urlparse(cluster_status['mgrmap']['services']['prometheus'])
    prom_ip, prom_port = prom_url.netloc.split(':')

    output = [
            {
                "name": "rook-ceph-mon-endpoints",
                "kind": "ConfigMap",
                "data": {
                    "data": "{}={}".format(mon_name, mon_ip),
                    "maxMonId": "0",
                    "mapping": "{}"
                    }
                },
            {
                "name": "rook-ceph-mon",
                "kind": "Secret",
                "data": {
                    "admin-secret": "admin-secret",
                    "fsid": cluster_status['fsid'],
                    "mon-secret": "mon-secret"
                    }
                },
            {
                "name": "rook-ceph-operator-creds",
                "kind": "Secret",
                "data": {
                    "userID": users['healthchecker']['name'],
                    "userKey": users['healthchecker']['key'],
                    }
                },
            {
                "name": "ceph-rbd",
                "kind": "StorageClass",
                "data": {
                    "pool": "{}-rbd".format(args.instance_name),
                    }
                },
            {
                "name": "monitoring-endpoint",
                "kind": "CephCluster",
                "data": {
                    "MonitoringEndpoint": prom_ip,
                    "MonitoringPort": prom_port,
                    }
                },
            {
                "name": "rook-csi-rbd-node",
                "kind": "Secret",
                "data": {
                    "userID": users['csi-rbd-node']['name'].replace('client.', ''),
                    "userKey": users['csi-rbd-node']['key'],
                    }
                },
            {
                    "name": "rook-csi-rbd-provisioner",
                    "kind": "Secret",
                    "data": {
                        "userID": users['csi-rbd-provisioner']['name'].replace('client.', ''),
                        "userKey": users['csi-rbd-provisioner']['key'],
                        }
                    }
            ]

    if args.use_cephfs:
        output.extend([
            {
                "name": "rook-csi-cephfs-provisioner",
                "kind": "Secret",
                "data": {
                    "adminID": users['csi-cephfs-provisioner']['name'].replace('client.', ''),
                    "adminKey": users['csi-cephfs-provisioner']['key'],
                    }
                },
            {
                "name": "rook-csi-cephfs-node",
                "kind": "Secret",
                "data": {
                    "adminID": users['csi-cephfs-node']['name'].replace('client.', ''),
                    "adminKey": users['csi-cephfs-node']['key'],
                    }
                },
            {
                "name": "cephfs",
                "kind": "StorageClass",
                "data": {
                    "fsName": "{}-fs".format(args.instance_name),
                    "pool": "cephfs.{}-fs.data".format(args.instance_name),
                    }
                }
            ])

    print(json.dumps(output, indent=2))



if __name__ == '__main__':
    main()
```

If you'd prefer a strictly manual process, you can fill in the
necessary values yourself.  The JSON produced by the above script
looks like the following, which is invalid JSON because I've use
inline comments to mark all the values which you would need to
provide:

```
[
  {
    "name": "rook-ceph-mon-endpoints",
    "kind": "ConfigMap",
    "data": {
      # The format is <mon_name>=<mon_endpoint>, and you only need to
      # provide a single mon address.
      "data": "ceph0=192.168.122.140:6789",
      "maxMonId": "0",
      "mapping": "{}"
    }
  },
  {
    "name": "rook-ceph-mon",
    "kind": "Secret",
    "data": {
      # Fill in the fsid of your Ceph cluster.
      "fsid": "c9c32c73-dac4-4cc9-8baa-d73b96c135f4",

      # Do **not** fill in these values, they are unnecessary. OCS
      # does not require admin access to your Ceph cluster.
      "admin-secret": "admin-secret",
      "mon-secret": "mon-secret"
    }
  },
  {
    "name": "rook-ceph-operator-creds",
    "kind": "Secret",
    "data": {
      # Fill in the  name and key for your healthchecker principal.
      # Note that here, unlike elsewhere in this JSON, you must
      # provide the "client." prefix to the principal name.
      "userID": "client.healthchecker-mycluster",
      "userKey": "<key>"
    }
  },
  {
    "name": "ceph-rbd",
    "kind": "StorageClass",
    "data": {
      # Fill in the name of your RBD pool.
      "pool": "mycluster-rbd"
    }
  },
  {
    "name": "monitoring-endpoint",
    "kind": "CephCluster",
    "data": {
      # Fill in the address and port of the Ceph cluster prometheus 
      # endpoint.
      "MonitoringEndpoint": "192.168.122.140",
      "MonitoringPort": "9283"
    }
  },
  {
    "name": "rook-csi-rbd-node",
    "kind": "Secret",
    "data": {
      # Fill in the name and key of the csi-rbd-node principal.
      "userID": "csi-rbd-node-mycluster",
      "userKey": "<key>"
    }
  },
  {
    "name": "rook-csi-rbd-provisioner",
    "kind": "Secret",
    "data": {
      # Fill in the name and key of your csi-rbd-provisioner
      # principal.
      "userID": "csi-rbd-provisioner-mycluster",
      "userKey": "<key>"
    }
  },
  {
    "name": "rook-csi-cephfs-provisioner",
    "kind": "Secret",
    "data": {
      # Fill in the name and key of your csi-cephfs-provisioner
      # principal.
      "adminID": "csi-cephfs-provisioner-mycluster",
      "adminKey": "<key>"
    }
  },
  {
    "name": "rook-csi-cephfs-node",
    "kind": "Secret",
    "data": {
      # Fill in the name and key of your csi-cephfs-node principal.
      "adminID": "csi-cephfs-node-mycluster",
      "adminKey": "<key>"
    }
  },
  {
    "name": "cephfs",
    "kind": "StorageClass",
    "data": {
      # Fill in the name of your CephFS filesystem and the name of the
      # associated data pool.
      "fsName": "mycluster-fs",
      "pool": "cephfs.mycluster-fs.data"
    }
  }
]
```

## Associated Bugs

I've opened several bug reports to see about adressing some of these
issues:

- [#1996833](https://bugzilla.redhat.com/show_bug.cgi?id=1996833)
  "ceph-external-cluster-details-exporter.py should have a read-only
  mode"
- [#1996830](https://bugzilla.redhat.com/show_bug.cgi?id=1996830) "OCS
  external mode should allow specifying names for all Ceph auth
  principals"
- [#1996829](https://bugzilla.redhat.com/show_bug.cgi?id=1996829)
  "Permissions assigned to ceph auth principals when using external
  storage are too broad"
