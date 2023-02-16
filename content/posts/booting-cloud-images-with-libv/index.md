---
aliases:
- /2015/03/10/booting-cloud-images-with-libvirt/
- /post/2015-03-10-booting-cloud-images-with-libvirt
categories:
- tech
date: '2015-03-10'
tags:
- fedora
- cloud-init
title: Booting cloud images with libvirt
---

Most major distributions now provide "cloud-enabled" images designed
for use in cloud environments like OpenStack and AWS.  These images
are usually differentiated by (a) being relatively small, and (b) running
[cloud-init][] at boot to perform initial system configuration tasks
using metadata provided by the cloud environment.

[cloud-init]: http://cloudinit.readthedocs.org/

Because of their small size and support for automatic configuration
(including such useful tasks as provisioning ssh keys), these images
are attractive for use *outside* of a cloud environment.
Unfortunately, when people first try to boot them they are met with
frustration as first the image takes forever to boot as it tries to
contact a non-existent metadata service, and then when it finally does
boot they are unable to log in because the images typically only
support key-based login.

Fortunately, there are ways to work around these issues.  In addition
to working with various network-accessible metadata services,
[cloud-init][] is also able to read configuration information from an
attached [virtual] CD-ROM device.  This is known as a "configuration
drive", and it is relatively easy to create.

For this purpose, the simplest solution is use [cloud-init][]'s "no
cloud" data source.  For this, we need to create an ISO filesystem
creating two files, `meta-data` and (optionally) `user-data`.

## The meta-data file

The `meta-data` file is effectively a YAML version of the data
typically available in the EC2 metadata service, and will look
something like this:

    instance-id: my-instance-id
    local-hostname: my-host-name

The `instance-id` key is required. You can also include SSH public
keys in this file, like this:

    instance-id: my-instance-id
    local-hostname: my-host-name
    public-keys:
      - ssh-rsa AAAAB3NzaC1...

You will see examples that place ssh keys in the `user-data` file
instead, but I believe this is the wrong solution, since it forces you
to use a "cloud-config" format `user-data` file.  Putting ssh keys
into the `meta-data` provides you more flexibility with your
`user-data` content.

## The user-data file

The `user-data` can be any of the various formats [supported by
cloud-init][formats].  For example, it could simply be a shell script:

    #!/bin/sh

    yum -y install some-critical-package

Or it could be a [cloud-config][] YAML document:

    #cloud-config

    write-files:
      - path: /etc/profile.d/gitaliases.sh
        content: |
          alias gc="git commit"
          alias gcv="git commit --no-verify"
    runcmd:
      - setenforce 1

[formats]: http://cloudinit.readthedocs.org/en/latest/topics/format.html
[cloud-config]: http://cloudinit.readthedocs.org/en/latest/topics/examples.html#yaml-examples

## Putting it all together

Once you have created your `meta-data` and `user-data` files, you can
create the configuration drive like this:

    genisoimage -o config.iso -V cidata -r -J meta-data user-data

To boot an instance using this configuration drive, you could do
something like this:

    virt-install -n example -r 512 -w network=default \
      --disk vol=default/fedora-21-cloud.qcow2 --import \
      --disk path=config.iso,device=cdrom

(This assumes, obviously, that you have an image named
`fedora-21-cloud.qcow2` available in libvirt's `default` storage
pool.)

## A little automation

I have written a [create-config-drive][] script that will automate
this process.  With this script available, the above process is
simply:

    create-config-drive -k ~/.ssh/id_rsa.pub -u user-data config.iso
    adding pubkey from /home/lars/.ssh/id_rsa.pub
    adding user data from userdata
    generating configuration image at config.iso

[create-config-drive]: https://github.com/larsks/virt-utils/blob/master/create-config-drive