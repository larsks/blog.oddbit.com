---
aliases:
- /2015/10/26/ansible-20-new-openstack-modules/
- /post/2015-10-26-ansible-20-new-openstack-modules
categories:
- tech
date: '2015-10-26'
tags:
- ansible
- openstack
- ansible_20_series
- pull-request
title: 'Ansible 2.0: New OpenStack modules'
---

This is the second in a loose sequence of articles looking at new
features in Ansible 2.0.  In the previous article I looked at the
[Docker connection driver][].  In this article, I would like to
provide an overview of the new-and-much-improved suite of modules for
interacting with an [OpenStack][] environment, and provide a few
examples of their use.

[docker connection driver]: {{< ref "ansible-20-the-docker-connecti" >}}
[openstack]: http://www.openstack.org/

In versions of Ansible prior to 2.0, there was a small collection of
OpenStack modules.  There was the minimum necessary to boot a Nova
instance:

- `glance_image.py`
- `keystone_user.py`
- `nova_compute.py`
- `nova_keypair.py`

And a collection of modules for interacting with [Neutron][] (previously
Quantum):

[neutron]: https://wiki.openstack.org/wiki/Neutron

- `quantum_floating_ip_associate.py`
- `quantum_floating_ip.py`
- `quantum_network.py`
- `quantum_router_gateway.py`
- `quantum_router_interface.py`
- `quantum_router.py`
- `quantum_subnet.py`

While functional, these modules did not provide very comprehensive
coverage of even basic OpenStack services, and they suffered from
having a great deal of duplicated code (which made ensuring
consistent behavior across all the modules more difficult).  The
behavior of these modules was not always what you would expect (e.g.,
the `nova_compute` module would return information in different forms
depending on whether it had to create an instance or not).

## Throwing Shade

The situation is much improved in Ansible 2.0, which introduces a new
suite of OpenStack modules in which the common code has been factored
out into the [Shade][] project, a Python package that provides a
simpler interface to OpenStack than is available using the native
clients.  Collecting this code in one place will help ensure both that
these Ansible modules share consistent behavior and that they are
easier to maintain.

[shade]: https://pypi.python.org/pypi/shade

There are modules for managing Keystone:

- `os_auth.py`
- `os_user_group.py`
- `os_user.py`

Glance:

- `os_image_facts.py`
- `os_image.py`

Cinder:

- `os_server_volume.py`
- `os_volume.py`

Nova:

- `os_keypair.py`
- `os_nova_flavor.py`
- `os_server_actions.py`
- `os_server_facts.py`
- `os_server.py`

Ironic:

- `os_ironic_node.py`
- `os_ironic.py`

Neutron and Nova Networking:

- `os_floating_ip.py`
- `os_network.py`
- `os_networks_facts.py`
- `os_port.py`
- `os_router.py`
- `os_security_group.py`
- `os_security_group_rule.py`
- `os_subnet.py`
- `os_subnets_facts.py`

and Swift:

- `os_object.py`

## Authentication

Shade uses the [os-client-config][] library to configure
authentication credentials for  your OpenStack environment.

[os-client-config]: https://pypi.python.org/pypi/os-client-config/

In the absence of any authentication information provided in your
Ansible playbook, these modules will attempt to use the standard suite
of `OS_*` variables (`OS_USERNAME`, `OS_PASSWORD`, etc).  This is fine
for testing, but you usually want to provide some sort of
authentication configuration in your Ansible environment.

You can provide credentials directly in your plays by providing an
`auth` argument to any of the modules.  For example:

    - os_image:
        auth:
          auth_url: http://openstack.local:5000/v2.0
          username: admin
          password: secret
          project_name: admin
        [...]

But that can get complicated, especially if you are maintaining
multiple sets of credentials.  The `shade` library allows you to
manage credentials in a file named (by default) `clouds.yml`, which
`shade` searches for in:

- The current directory
- `$HOME/.config/openstack/`
- `/etc/xdg/openstack/`
- `/etc/openstack`

This file may contain credentials for one or more cloud environments,
for example:

    clouds:
      testing:
        auth:
          auth_url: http://openstack.local:5000/v2.0
          username: admin
          password: secret
          project_name: admin
    
If you have the above in `clouds.yml` along with your playbook, the
above `os_image` example can be rewritten as:

    - os_image:
        cloud: testing
        [...]

## Return values

The new modules all return useful information about the objects they
have created.  For example, if you create a network using
[os_network][] and register that result:

[os_network]: http://docs.ansible.com/ansible/os_network_module.html

    - os_network:
        cloud: testing
        name: mynetwork
      register: mynetwork

You'll get back a dictionary containing a top-level `id` attribute,
which is the UUID of the created network, along with a `network`
attribute containing a dictionary of information about the created
object.  The [debug][] module is an excellent tool for exploring these
return values.  If we put the following in our playbook immediately
after the above task:

[debug]: http://docs.ansible.com/ansible/debug_module.html

    - debug:
        var: mynetwork

We would get output that looks something like:

    ok: [localhost] => {
        "changed": false, 
        "mynetwork": {
            "changed": true, 
            "id": "02b77e32-794a-4102-ab1b-1b90e6d4d92f", 
            "invocation": {
                "module_args": {
                    "cloud": "testing", 
                    "name": "mynetwork"
                }, 
                "module_name": "os_network"
            }, 
            "network": {
                "admin_state_up": true, 
                "id": "02b77e32-794a-4102-ab1b-1b90e6d4d92f", 
                "mtu": 0, 
                "name": "mynetwork", 
                "provider:network_type": "vxlan", 
                "provider:physical_network": null, 
                "provider:segmentation_id": 79, 
                "router:external": false, 
                "shared": false, 
                "status": "ACTIVE", 
                "subnets": [], 
                "tenant_id": "349a8b95c5ad4a3383149f65f8c44cff"
            }
        }
    }

## Examples

I have written a set of basic [integration tests][] for these modules.
I hope the pull request is merged, but even if not it provides an
example of how to make use of many of these new modules.

[integration tests]: https://github.com/ansible/ansible/pull/12875

I'd like to present a few brief examples here to give you a sense of
what working with the new modules is like.

### Uploading an image to Glance

The [os_image][] module is used to upload an image to Glance.  Assuming
that you have file named `cirros.qcow2` available locally, this will
create an image named `cirros` in Glance:

[os_image]: http://docs.ansible.com/ansible/os_image_module.html

    - os_image:
        cloud: testing
        name: cirros
        state: present
        disk_format: qcow2
        container_format: bare
        filename: cirros.qcow2

### Booting a Nova server

The [os_server][] module, which is used for booting virtual servers
("instances") in Nova, replaces the [nova_compute][] module available
in Ansible versions before 2.0:

[nova_compute]: http://docs.ansible.com/ansible/nova_compute_module.html
[os_server]: http://docs.ansible.com/ansible/os_server_module.html

    - name: create a nova server
      os_server:
        cloud: testing
        name: myserver
        state: present
        nics:
          - net-name: private
        image: cirros
        flavor: m1.small
        key_name: my_ssh_key

The `nics` parameter can accept net names, net ids, port names, and
port ids.  So you could also do this (assuming you were attaching your
server to two different tenant networks):

    nics:
      - net-id: c875770c-a20b-45b5-a9da-5aca97153053
      - net-name: private

The above examples are using a YAML list of dictionaries to provide
the information.  You can also pass in a comma-delimited key=value
string, like this:

    nics: net-name=private,net-name=database

This syntax is particular useful if you are running ad-hoc commands on
the command line:

    ansible localhost -m os_server -a '
      cloud=testing name=myserver nics=net-name=private
      image=cirros flavor=m1.small key_name=my_ssh_key'

### Adding a Nova server to your Ansible inventory

I'd like to conclude this post with a longer example, that
demonstrates how you can use the [add_host][] module to add a freshly
created server to your inventory, and then target that new server in
your playbook.  I've split up this playbook with commentary; in
practice, the pre-formatted text in this section would all be in a
single playbook (like [this][playbook]).

[playbook]: playbook.yml
[add_host]: http://docs.ansible.com/ansible/add_host_module.html

    - hosts: localhost
      tasks:                                                                    
                                                                                
This first task boots the server. The values for `image`, `nics`, and
`key_name will need to be adjusted for your environment.

        - os_server:
            cloud: testing
            name: myserver
            image: centos-7-atomic
            nics:
              - net-name: private
            flavor: m1.small
            key_name: lars
            auto_ip: true
          register: myserver

This `debug` entry simply shows us what values were returned in the
`myserver` variable.

        - debug:
            var: myserver

Now we add the new host to our Ansible inventory.  For this to work,
you need to have assigned a floating ip to the server (either using
`auto_ip`, as in this example, or by assigning one explicitly), and
you need to be running this playbook somewhere that has a route to the
floating ip address.

        - add_host:
            name: myserver
            groups: openstack
            ansible_host: "{{myserver.server.public_v4}}"
            ansible_user: centos
            ansible_become: true

Note that in the above play you can't use information from the
inventory because that new host won't exist in the inventory until
*after* this play completes.

We'll need to wait for the server to finish booting and provisioning
before we are able to target it with ansible.  A typical cloud image
is configured to run [cloud-init][] when it boots, which will take
care of a number of initial configuration tasks, including
provisioning the ssh key we configured using `os_server`.  Until this
process is complete, we won't have remote access to the server.

[cloud-init]: https://cloudinit.readthedocs.org/en/latest/

We can't use the `wait_for` module because that will only
check for an open port. Instead, we use a [do-until loop][until] to
wait until we are able to successfully run a command on the server via
ssh.

[until]: http://docs.ansible.com/ansible/playbooks_loops.html#do-until-loops

        - command: >
            ssh -o BatchMode=yes
            centos@{{myserver.server.public_v4}} true
          register: result
          until: result|success
          retries: 300
          delay: 5

Now that we have added the new server to our inventory
we can target it in subsequent plays (such as this one):

    - hosts: myserver
      tasks:

        - service:
            name: docker
            state: running
            enabled: true
