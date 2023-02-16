---
aliases:
- /2015/09/29/migrating-cinder-volumes-between-openstack-environments/
- /post/2015-09-29-migrating-cinder-volumes-between-openstack-environments
categories:
- tech
date: '2015-09-29'
tags:
- openstack
- cinder
title: Migrating Cinder volumes between OpenStack environments using shared NFS storage
---

Many of the upgrade guides for OpenStack focus on in-place upgrades to
your OpenStack environment.  Some organizations may opt for a less
risky (but more hardware intensive) option of setting up a parallel
environment, and then migrating data into the new environment.  In
this article, we look at how to use Cinder backups with a shared NFS
volume to facilitate the migration of Cinder volumes between two
different OpenStack environments.

## Overview

This is how we're going to proceed:

In the source environment:

1. Configure Cinder for NFS backups
1. Create a backup
1. Export the backup metadata

In the target environment:

1. Configure Cinder for NFS backups
1. Import the backup metadata
1. Create a new volume matching the size of the source volume
1. Restore the backup to the new volume

## Cinder configuration

We'll be using the NFS backup driver for cinder, which means
`cinder.conf` must contain:

    backup_driver=cinder.backup.drivers.nfs

And you need to configure an NFS share to use for backups:

    backup_share=fileserver:/vol/backups

Cinder in both environments should be pointing at the same
`backup_share`.  This is how we make backups made in the source
environment available in the target environment -- they will both have
access to the same storage, so that we only need to copy the metadata
into the target environment.

After making changes to your Cinder configuration
you will need to restart Cinder.  If you are using RDO or RHEL-OSP,
this is:

    openstack-service restart cinder

## Creating a backup

Assume we have a volume named `testvol` that is currently attached to
a running Nova server.  The output of `cinder list` looks like:

    $ cinder list
    +----------...+--------+--------------+------+...+----------+-------------...+
    |   ID     ...| Status | Display Name | Size |...| Bootable |  Attached to...|
    +----------...+--------+--------------+------+...+----------+-------------...+
    | bec9b02f-...| in-use |   testvol    |  1   |...|  false   | d97e9193-cf2...|
    +----------...+--------+--------------+------+...+----------+-------------...+

We can try to create a backup of this using `cinder backup-create`:

    $ cinder backup-create testvol

But this will fail because the volume is currently attached to a Nova
server:

    ERROR: Invalid volume: Volume to be backed up must be available
    (HTTP 400) (Request-ID: req-...)
    
There are two ways we can deal with this:

1. We can pass the `--force` flag to `cinder backup-create`, which
   will allow the backup to continue even if the source volume is
   attached.  This should be done with care, because the on-disk
   filesystem may not be in consistent state.

     The `--force` flag was introduced in OpenStack Liberty.  If you
     are using an earlier OpenStack release you will need to use the
     following procedure.

1. We can make the volume available by detaching it from the server.
   In this case, you probably want to shut down the server first:

        $ nova stop d97e9193-cf2c-41c4-afa2-fdd201b575d9
        Request to stop server d97e9193-cf2c-41c4-afa2-fdd201b575d9 has
        been accepted.

    And then detach the volume:

        $ nova volume-detach \
            d97e9193-cf2c-41c4-afa2-fdd201b575d9 \
            bec9b02f-f66f-4f15-a254-9acebd9c7c34

1. Now the backup will start successfully:

        # cinder backup-create testvol
        +-----------+--------------------------------------+
        |  Property |                Value                 |
        +-----------+--------------------------------------+
        |     id    | 96128a75-e143-4d8a-9b93-e246af8e6a7d |
        |    name   |                 None                 |
        | volume_id | bec9b02f-f66f-4f15-a254-9acebd9c7c34 |
        +-----------+--------------------------------------+

At this point, you can use the `cinder backup-list` command to see the
status of the backup.  Initially it will be in state `creating`:

    $ cinder backup-list
    +----------...+------------...+----------+------+------+...+----------------...+
    | ID       ...| Volume ID  ...| Status   | Name | Size |...| Container      ...|
    +----------...+------------...+----------+------+------+...+----------------...+
    | 96128a75-...| bec9b02f-f6...| creating |  -   |  1   |...| 96/12/96128a75-...|
    +----------...+------------...+----------+------+------+...+----------------...+

When the backup is finished, the status will read `available`:

    $ cinder backup-list
    +----------...+------------...+-----------+------+------+...+----------------...+
    | ID       ...| Volume ID  ...| Status    | Name | Size |...| Container      ...|
    +----------...+------------...+-----------+------+------+...+----------------...+
    | 96128a75-...| bec9b02f-f6...| available |  -   |  1   |...| 96/12/96128a75-...|
    +----------...+------------...+-----------+------+------+...+----------------...+

At this point, you may want to re-attach the volume to your Nova server and
restart the server:

        $ nova volume-attach \
            d97e9193-cf2c-41c4-afa2-fdd201b575d9 \
            bec9b02f-f66f-4f15-a254-9acebd9c7c34
        $ nova start d97e9193-cf2c-41c4-afa2-fdd201b575d9

## Exporting the backup

Now that we have successfully created the backup, we need to export
the Cinder metadata regarding the backup using the `cinder
backup-export` command (which can only be run by a user with `admin`
privileges):

    $ cinder backup-export 96128a75-e143-4d8a-9b93-e246af8e6a7d

This will return something like the following:

    +----------------+------------------------------------------------------------------------------+
    |    Property    |                                    Value                                     |
    +----------------+------------------------------------------------------------------------------+
    | backup_service |                          cinder.backup.drivers.nfs                           |
    |   backup_url   | eyJzdGF0dXMiOiAiYXZhaWxhYmxlIiwgIm9iamVjdF9jb3VudCI6IDIsICJkZWxldGVkX2F0Ijog |
    |                | bnVsbCwgInNlcnZpY2VfbWV0YWRhdGEiOiAiYmFja3VwIiwgInVzZXJfaWQiOiAiYTY1MzQ5NzU5 |
    |                | YjZmNGVjNWEwYmIwY2MzZmViMWU5ZmEiLCAic2VydmljZSI6ICJjaW5kZXIuYmFja3VwLmRyaXZl |
    |                | cnMubmZzIiwgImF2YWlsYWJpbGl0eV96b25lIjogIm5vdmEiLCAiZGVsZXRlZCI6IGZhbHNlLCAi |
    |                | Y3JlYXRlZF9hdCI6ICIyMDE1LTA5LTI5VDE4OjU5OjEwLjAwMDAwMCIsICJ1cGRhdGVkX2F0Ijog |
    |                | IjIwMTUtMDktMjlUMTg6NTk6MzEuMDAwMDAwIiwgImRpc3BsYXlfZGVzY3JpcHRpb24iOiBudWxs |
    |                | LCAicGFyZW50X2lkIjogbnVsbCwgImhvc3QiOiAiaWJtLWhzMjItMDMucmh0cy5lbmcuYnJxLnJl |
    |                | ZGhhdC5jb20iLCAiY29udGFpbmVyIjogIjk2LzEyLzk2MTI4YTc1LWUxNDMtNGQ4YS05YjkzLWUy |
    |                | NDZhZjhlNmE3ZCIsICJ2b2x1bWVfaWQiOiAiYmVjOWIwMmYtZjY2Zi00ZjE1LWEyNTQtOWFjZWJk |
    |                | OWM3YzM0IiwgImRpc3BsYXlfbmFtZSI6IG51bGwsICJmYWlsX3JlYXNvbiI6IG51bGwsICJwcm9q |
    |                | ZWN0X2lkIjogImJjYWUzM2JkZjViODRkYzlhYjljYTY1MThhNDM4NTYxIiwgImlkIjogIjk2MTI4 |
    |                |         YTc1LWUxNDMtNGQ4YS05YjkzLWUyNDZhZjhlNmE3ZCIsICJzaXplIjogMX0=         |
    |                |                                                                              |
    +----------------+------------------------------------------------------------------------------+

That giant block of text labeled `backup_url` is not, in fact, a URL.
In this case, the actual content is a base64 encoded JSON string.  You
will need to copy the base64 data to your target OpenStack
environment.  You can extract just the base64 data like this:

    cinder backup-export 96128a75-e143-4d8a-9b93-e246af8e6a7d |
      sed -n '/backup_url/,$ s/|.*|  *\(.*\) |/\1/p'

Which will give you:

    eyJzdGF0dXMiOiAiYXZhaWxhYmxlIiwgIm9iamVjdF9jb3VudCI6IDIsICJkZWxldGVkX2F0Ijog
    bnVsbCwgInNlcnZpY2VfbWV0YWRhdGEiOiAiYmFja3VwIiwgInVzZXJfaWQiOiAiYTY1MzQ5NzU5
    YjZmNGVjNWEwYmIwY2MzZmViMWU5ZmEiLCAic2VydmljZSI6ICJjaW5kZXIuYmFja3VwLmRyaXZl
    cnMubmZzIiwgImF2YWlsYWJpbGl0eV96b25lIjogIm5vdmEiLCAiZGVsZXRlZCI6IGZhbHNlLCAi
    Y3JlYXRlZF9hdCI6ICIyMDE1LTA5LTI5VDE4OjU5OjEwLjAwMDAwMCIsICJ1cGRhdGVkX2F0Ijog
    IjIwMTUtMDktMjlUMTg6NTk6MzEuMDAwMDAwIiwgImRpc3BsYXlfZGVzY3JpcHRpb24iOiBudWxs
    LCAicGFyZW50X2lkIjogbnVsbCwgImhvc3QiOiAiaWJtLWhzMjItMDMucmh0cy5lbmcuYnJxLnJl
    ZGhhdC5jb20iLCAiY29udGFpbmVyIjogIjk2LzEyLzk2MTI4YTc1LWUxNDMtNGQ4YS05YjkzLWUy
    NDZhZjhlNmE3ZCIsICJ2b2x1bWVfaWQiOiAiYmVjOWIwMmYtZjY2Zi00ZjE1LWEyNTQtOWFjZWJk
    OWM3YzM0IiwgImRpc3BsYXlfbmFtZSI6IG51bGwsICJmYWlsX3JlYXNvbiI6IG51bGwsICJwcm9q
    ZWN0X2lkIjogImJjYWUzM2JkZjViODRkYzlhYjljYTY1MThhNDM4NTYxIiwgImlkIjogIjk2MTI4
    YTc1LWUxNDMtNGQ4YS05YjkzLWUyNDZhZjhlNmE3ZCIsICJzaXplIjogMX0=

While not critical to this process, it may be interesting to see that
this string actually decodes to:

    {
        "availability_zone": "nova",
        "container": "96/12/96128a75-e143-4d8a-9b93-e246af8e6a7d",
        "created_at": "2015-09-29T18:59:10.000000",
        "deleted": false,
        "deleted_at": null,
        "display_description": null,
        "display_name": null,
        "fail_reason": null,
        "host": "ibm-hs22-03.rhts.eng.brq.redhat.com",
        "id": "96128a75-e143-4d8a-9b93-e246af8e6a7d",
        "object_count": 2,
        "parent_id": null,
        "project_id": "bcae33bdf5b84dc9ab9ca6518a438561",
        "service": "cinder.backup.drivers.nfs",
        "service_metadata": "backup",
        "size": 1,
        "status": "available",
        "updated_at": "2015-09-29T18:59:31.000000",
        "user_id": "a65349759b6f4ec5a0bb0cc3feb1e9fa",
        "volume_id": "bec9b02f-f66f-4f15-a254-9acebd9c7c34"
    }

## Importing the backup

In the target OpenStack environment, you need to import the backup
metadata to make Cinder aware of the backup.  You do this with the
`cinder backup-import` command, which requires both a `backup_service`
parameter and a `backup_url`.  These are the values produces by the
`cinder backup-export` command in the previous step.

Assuming that we have dumped the base64 data into a file named
`metadata.txt`, we can import the metadata using the following
command:

    # cinder backup-import cinder.backup.drivers.nfs $(tr -d '\n' < metadata.txt)
    +----------+--------------------------------------+
    | Property |                Value                 |
    +----------+--------------------------------------+
    |    id    | a23891b2-e757-4d8f-9623-3d982e5616cb |
    |   name   |                 None                 |
    +----------+--------------------------------------+

And now if we run `cinder backup-list` we should see a new backup
available:

    $ cinder backup-list
    +----------...+----------...+-----------+------+------+...+-----------...+
    | ID       ...| Volume ID...|   Status  | Name | Size |...| Container ...|
    +----------...+----------...+-----------+------+------+...+-----------...+
    | a23891b2-...| 0000-0000...| available |  -   |  1   |...| 96/12/9612...|
    +----------...+----------...+-----------+------+------+...+-----------...+

## Creating a new volume

At this point, we could simply run `cinder backup-restore` on the
target system, and Cinder would restore the data onto a new volume
owned by the `admin` user.  If you want to restore to a volume owned
by another user, it is easiest to first create the volume as that
user.  You will want to make sure that the size is at least as large
as the source volume:

    $ cinder create --display_name mydata 1
    +---------------------------------------+--------------------------------------+
    |                Property               |                Value                 |
    +---------------------------------------+--------------------------------------+
    [...]
    |                   id                  | 145277e1-4733-4374-9b9c-677cb5334379 |
    [...]
    +---------------------------------------+--------------------------------------+

Note that is is possible to transfer a volume between tenants using
the `cinder transfer-create` and `cinder transfer-accept` commands,
but I will not be covering that in this article.

## Restoring the backup

Now that we have created a target volume we can restore the data from
our backup:

    $ cinder backup-restore --volume 145277e1-4733-4374-9b9c-677cb5334379 \
        a23891b2-e757-4d8f-9623-3d982e5616cb
    +-----------+--------------------------------------+
    |  Property |                Value                 |
    +-----------+--------------------------------------+
    | backup_id | a23891b2-e757-4d8f-9623-3d982e5616cb |
    | volume_id | 145277e1-4733-4374-9b9c-677cb5334379 |
    +-----------+--------------------------------------+

While the backup is running the backup status will be `restoring`:

    +----------...+------------...+-----------+------+------+...+----------------...+
    | ID       ...| Volume ID  ...| Status    | Name | Size |...| Container      ...|
    +----------...+------------...+-----------+------+------+...+----------------...+
    | a23891b2-...| 0000-0000-0...| restoring |  -   |  1   |...| 96/12/96128a75-...|
    +----------...+------------...+-----------+------+------+...+----------------...+

When the backup is complete that status will be `available`:

    +----------...+------------...+-----------+------+------+...+----------------...+
    | ID       ...| Volume ID  ...| Status    | Name | Size |...| Container      ...|
    +----------...+------------...+-----------+------+------+...+----------------...+
    | a23891b2-...| 0000-0000-0...| available |  -   |  1   |...| 96/12/96128a75-...|
    +----------...+------------...+-----------+------+------+...+----------------...+

## Verification

If you spawn a Nova server in your target environment and attach the
volume we just created, you should find that it contains the same data
as the source volume contained at the time of the backup.

## For more information

The [Cloud Adminstrator Guide][cloudadmin] has more information about
[volume backups and restores][cloudadmin/backup] and [managing backup
metadata][cloudadmin/metadata].

[cloudadmin]: http://docs.openstack.org/admin-guide-cloud/
[cloudadmin/backup]: http://docs.openstack.org/admin-guide-cloud/blockstorage_volume_backups.html
[cloudadmin/metadata]: http://docs.openstack.org/admin-guide-cloud/blockstorage_volume_backups_export_import.html