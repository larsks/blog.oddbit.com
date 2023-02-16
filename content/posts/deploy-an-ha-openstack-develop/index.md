---
aliases:
- /2016/02/19/deploy-an-ha-openstack-development-envir/
- /post/2016-02-19-deploy-an-ha-openstack-development-envir
categories:
- tech
date: '2016-02-19'
tags:
- openstack
- tripleo
- rdo
- ansible
title: 'Deploying an HA OpenStack development environment with tripleo-quickstart

  '
---

In this article I would like to introduce [tripleo-quickstart][], a
tool that will automatically provision a virtual environment and then
use [TripleO][] to deploy an HA OpenStack on top of it.

[tripleo]: http://docs.openstack.org/developer/tripleo-docs/
[tripleo-quickstart]: https://github.com/redhat-openstack/tripleo-quickstart

## Introducing Tripleo-Quickstart

The goal of the [Tripleo-Quickstart][] project is to replace the
`instack-virt-setup` tool for quickly setting up virtual TripleO
environments, and to ultimately become the tool used by both
developers and upstream CI for this purpose.  The project is a set of
[Ansible][] playbooks that will take care of:

- Creating virtual undercloud node
- Creating virtual overcloud nodes
- Deploying the undercloud
- Deploying the overcloud
- Validating the overcloud

In this article, I will be using `tripleo-quickstart` to set up a
development environment on a 32GB desktop.  This is probably the
minimum sized system if your goal is to create an HA install (a
single controller/single compute environment could be deployed on
something smaller).

## Requirements

Before we get started, you will need:

- A target system with at least 32GB of RAM.

- Ansible 2.0.x.  This is what you get if you `pip install ansible`;
  it is also available in the Fedora `updates-testing` repository and
  in the EPEL `epel-testing` repository.

    Do **not** use Ansible from the HEAD of the git repository; the
    development version is not necessarily backwards compatible with
    2.0.x and may break in unexpected ways.

- A user account on the target system with which you can (a) log in
  via ssh without a password and (b) use `sudo` without a password to
  gain root privileges.  In other words, this should work:

          ssh -tt targetuser@targethost sudo echo it worked

    Your *targetuser* could be `root`, in which case the `sudo` is
    superfluous and you should be all set.

- A copy of the tripleo-quickstart repository:

        git clone https://github.com/redhat-openstack/tripleo-quickstart/

The remainder of this document assumes that you are running things
from inside the `tripleo-quickstart` directory.

## The quick way

If you just want to take things out for a spin using the defaults
*and* you can ssh to your target host as `root`, you can skip the
remainder of this article and just run:

    ansible-playbook playbooks/centosci/minimal.yml \
      -e virthost=my.target.host

Or for an HA deployment:

    ansible-playbook playbooks/centosci/ha.yml \
      -e virthost=my.target.host

(Where you replace `my.target.host` with the hostname of the host on
which you want to install your virtual environment.)

In the remainder of this article I will discuss ways in which you can
customize this process (and make subsequent deployments faster).

## Create an inventory file

An inventory file tells Ansible to which hosts it should connect and
provides information about how it should connect.  For the quickstart,
your inventory needs to have your target host listed in the `virthost`
group.  For example:

    [virthost]
    my.target.host ansible_user=targetuser

I'm going to assume you put this into a file named `inventory`.

## Creating a playbook

A playbook tells Ansible what do to do.

First, we want to tear down any existing virtual environment, and then
spin up a new undercloud node and create guests that will be used as
overcloud nodes. We do this with the `libvirt/teardown` and
`libvirt/setup` roles:

    - hosts: virthost
      roles:
        - libvirt/teardown
        - libvirt/setup

The next play will generate an Ansible inventory file (by default
`$HOME/.quickstart/hosts`) that we can use in the future to refer to
our deployment:

    - hosts: localhost
      roles:
        - rebuild-inventory

Lastly, we install the undercloud host and deploy the overcloud:

    - hosts: undercloud
      roles:
        - overcloud

Put this content in a file named `ha.yml` (the actual name doesn't
matter, but this gives us something to refer to later on in this
article).

## Configuring the deployment

Before we run tripleo-quickstart, we need to make a few configuration
changes. We'll do this by creating a [YAML][] file that describes our
configuration, and we'll feed this to ansible using the [-e
@filename.yml][extra-vars] syntax.

[extra-vars]: http://docs.ansible.com/ansible/playbooks_variables.html#passing-variables-on-the-command-line

### Describing your virtual servers

By default, tripleo-quickstart will deploy an environment consisting
of four overcloud nodes:

- 3 controller nodes
- 1 compute node

All of these will have 4GB of memory, which when added to the default
overcloud node size of 12GB comes to a total memory footprint of 24GB.
These defaults are defined in
`playbooks/roles/nodes/defaults/main.yml`.  There are a number of ways
we can override this default configuration.

To simply change the amount of memory assigned to each class of
server, we can set the `undercloud_memory`, `control_memory`, and
`compute_memory` keys.  For example:

    control_memory: 6000
    compute_memory: 2048

To change the number of CPUs assigned to a server, we can change the
corresponding `_vcpu` key.  Your deployments will generally run faster
if your undercloud host has more CPUs available:

    undercloud_vcpu: 4

To change the number and type of nodes, you can provide an
`overcloud_nodes` key with entries for each virtual system.  The
default looks like this:

    overcloud_nodes:
      - name: control_0
        flavor: control
      - name: control_1
        flavor: control
      - name: control_2
        flavor: control

      - name: compute_0
        flavor: compute

To create a minimal environment with a single controller and a single
compute node, we could instead put the following into our configuration
file:

    overcloud_nodes:
      - name: control_0
        flavor: control
      - name: compute_0
        flavor: compute

You may intuit from the above examples that you can actually describe
custom flavors.  This is true, but is beyond the scope of this post;
take a look at `playbooks/roles/nodes/defaults/main.yml` for an
example.

### Configuring HA

To actually deploy an HA OpenStack environment, we need to pass a few
additional options to the `openstack overcloud deploy` command.  Based
on [the docs][tripleo-ha] I need:

[tripleo-ha]: http://docs.openstack.org/developer/tripleo-docs/basic_deployment/basic_deployment_cli.html#deploy-the-overcloud

    --control-scale 3 \
    -e /usr/share/openstack-tripleo-heat-templates/environments/puppet-pacemaker.yaml \
    --ntp-server pool.ntp.org

We configure deploy arguments in the `extra_args` variable, so for the
above configuration we would add:

    extra_args: >
      --control-scale 3
      -e /usr/share/openstack-tripleo-heat-templates/environments/puppet-pacemaker.yaml
      --ntp-server pool.ntp.org

### Configuring nested KVM

I want [nested KVM][nested] on my compute hosts,
which requires changes both to the libvirt XML used to deploy the
"baremetal" hosts and the nova.conf configuration.  I was able to
accomplish this by adding the following to the configuration:

[nested]: https://www.kernel.org/doc/Documentation/virtual/kvm/nested-vmx.txt

    baremetal_vm_xml: |
      <cpu mode='host-passthrough'/>
    libvirt_args: --libvirt-type kvm

For this to work, you will need to have your target host correctly
configured to support nested KVM, which generally means adding the
following to `/etc/modprobe.d/kvm.conf`:

    options kvm_intel nested=1

(And possibly unloading/reloading the `kvm_intel` module if it was
already loaded.)

### Disable some steps

The default behavior is to:

- Install the undercloud
- Deploy the overcloud
- Validate the overcloud

You can enable or disable individual steps with the following
variables:

- `step_install_undercloud`
- `step_deploy_overcloud`
- `step_validate_overcloud`

These all default to `true`.  If, for example, overcloud validation is
failing because of a known issue, we could add the following to
`nodes.yml`:

    step_validate_overcloud: false

## Pre-caching the undercloud image

Fetching the undercloud image from the CentOS CI environment can take
a really long time.  If you're going to be deploying often, you can
speed up this step by manually saving the image and the corresponding
`.md5` file to a file on your target host:

    mkdir -p /usr/share/quickstart_images/mitaka/
    cd /usr/share/quickstart_images/mitaka/
    wget https://ci.centos.org/artifacts/rdo/images/mitaka/delorean/stable/undercloud.qcow2.md5 \
      https://ci.centos.org/artifacts/rdo/images/mitaka/delorean/stable/undercloud.qcow2

And then providing the path to that file in the `url` variable when
you run the playbook.  I've added the following to my `nodes.yml`
file, but you could also do this on the command line:

    url: file:///usr/share/quickstart_images/mitaka/undercloud.qcow2

## Intermission

I've made the examples presented in this article available for
download at the following URLs:

- [ha.yml](ha.yml) playbook
- [nodes.yml](nodes.yml) example configuration file
- [nodes-minimal.yml](nodes-minimal.yml) example configuration file for a minimal environment

## Running tripleo-quickstart

With all of the above in place, we can run:

    ansible-playbook ha.yml -i inventory -e @nodes.yml

Which will proceed through the following phases:

### Tear down existing environment

This step deletes any libvirt guests matching the ones we are about to
deploy, removes the `stack` user from the target host, and otherwise
ensures a clean slate from which to start.

### Create overcloud vms

This uses the node definitions in `vm.overcloud.nodes` to create a set
of libvirt guests.  They will *not* be booted at this stage; that
happens later during the ironic discovery process.

### Fetch the undercloud image

This will fetch the undercloud appliance image either from the CentOS
CI environment or from wherever you point the `url` variable.

### Configure the undercloud image

This performs some initial configuration steps such as injecting ssh
keys into the image.

### Create undercloud vm

In this step, tripleo-quickstart uses the configured appliance image
to create a new `undercloud` libvirt guest.

### Install undercloud

This runs `openstack undercloud install`.

### Deploy overcloud

This does everything else:

- Discover the available nodes via the Ironic discovery process
- Use `openstack overcloud deploy` to kick off the provisioning
  process.  This feeds [Heat][] a collection of templates that will be
  used to configure the overcloud nodes.

## Accessing the undercloud

You can ssh directly into the undercloud host by taking advantage of
the ssh configuration that tripleo-quickstart generated for you.  By
default this will be `$HOME/.quickstart/ssh.config.ansible`, but you
can override that directory by specifying a value for the
`local_working_dir` variable when you run Ansible.  You use the `-F`
option to ssh to point it at that file:

    ssh -F $HOME/.quickstart/ssh.config.ansible undercloud

The configuration uses an ssh `ProxyConnection` configuration to
automatically proxy your connection to the undercloud vm through your
physical host.

## Accessing the overcloud hosts

Once you have logged into the undercloud, you'll need to source in
some credentials.  The file `stackrc` contains credentials for the
undercloud:

    . stackrc

Now you can run `nova list` to get a list of your overcloud nodes,
investigate the `overcloud` heat stack, and so forth:

    $ heat stack-list
    +----------...+------------+-----------------+--------------...+--------------+
    | id       ...| stack_name | stack_status    | creation_time...| updated_time |
    +----------...+------------+-----------------+--------------...+--------------+
    | b6cfd621-...| overcloud  | CREATE_COMPLETE | 2016-02-19T20...| None         |
    +----------...+------------+-----------------+--------------...+--------------+

You can find the ip addresses of your overcloud nodes by running `nova
list`:

    $ nova list
    +----------...+-------------------------+--------+...+---------------------+
    | ID       ...| Name                    | Status |...| Networks            |
    +----------...+-------------------------+--------+...+---------------------+
    | 1fc5d5e8-...| overcloud-controller-0  | ACTIVE |...| ctlplane=192.0.2.9  |
    | ab6439e8-...| overcloud-controller-1  | ACTIVE |...| ctlplane=192.0.2.10 |
    | 82e12f81-...| overcloud-controller-2  | ACTIVE |...| ctlplane=192.0.2.11 |
    | 53402a35-...| overcloud-novacompute-0 | ACTIVE |...| ctlplane=192.0.2.8  |
    +----------...+-------------------------+--------+...+---------------------+

You'll use the `ctlplane` address to log into each host as the
`heat-admin` user.  For example, to log into my compute host:

    $ ssh heat-admin@192.0.2.8

## Accessing the overcloud OpenStack environment

The file `overcloudrc` on the undercloud host has administrative
credentials for the overcloud environment:

    . overcloudrc

After sourcing in the overcloud credentials you can use OpenStack
clients to interact with your deployed cloud environment.

## If you find bugs

If anything in the above process doesn't work as described or
expected, feel free to visit the `#rdo` channel on [freenode][], or
open a bug report on the [issue tracker][].

[ansible]: http://ansible.com/
[heat]: https://wiki.openstack.org/wiki/Heat
[yaml]: http://yaml.org/
[triplep-ha]: MISSING!
[freenode]: https://freenode.net/
[issue tracker]: https://github.com/redhat-openstack/tripleo-quickstart/issues
