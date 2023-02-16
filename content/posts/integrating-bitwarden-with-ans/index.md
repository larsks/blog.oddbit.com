---
categories: [tech]
aliases: ["/2018/10/19/integrating-bitwarden-with-ans/"]
title: Integrating Bitwarden with Ansible
date: "2018-10-19"
tags:
- bitwarden
- security
- ansible
- pull-request
---

[Bitwarden][] is a password management service (like [LastPass][] or
[1Password][]). It's unique in that it is built entirely on open
source software.  In addition to the the web UI and mobile apps that
you would expect, Bitwarden also provides a [command-line tool][] for
interacting with the your password store.

[bitwarden]: https://bitwarden.com
[lastpass]: https://www.lastpass.com/
[1password]: https://1password.com/
[command-line tool]: https://help.bitwarden.com/article/cli/

At $WORK(-ish) we're looking into Bitwarden because we want a password
sharing and management solution that was better than dropping files
into  directories on remote hosts or sharing things over Slack.  At
the same time, we are also thinking about bringing more automation to
our operational environment, possibly by making more extensive use of
[Ansible][]. It looked like all the pieces were available to use
Bitwarden as a credential storage mechanism for Ansible playbooks, so
I set out to write a lookup plugin to implement the integration...

[ansible]: https://ansible.com

...only to find that I was not the first person to have this idea;
Matt Stofko [beat me to it][].  While it worked, the directory
structure of Matt's repository made it difficult to integrate into an
existing Ansible project. It was also missing some convenience
features I wanted to see, so I have submitted {{< pull-request "c0sco/ansible-modules-bitwarden/1" >}} that
makes several changes to the module.

[beat me to it]: https://github.com/c0sco/ansible-modules-bitwarden/

You can find my fork of the Bitwarden lookup plugin at
<https://github.com/larsks/ansible-modules-bitwarden>.

## Make it installable

By re-arranging the repository to following the standard Ansible role
structure, it is now possible to install it either a submodule of your
own git repository, or to install it using the `ansible-galaxy` tool:

    ansible-galaxy install git+https://github.com/larsks/ansible-modules-bitwarden

This command would place the role in `$HOME/.ansible/roles`, where it
will be available to any playbooks you run on your system.

## Add explicit support for custom fields

While it was possible to access custom fields by fetching the complete
JSON representation of an item in Bitwarden and then querying the
resulting document, it wasn't particularly graceful.  I've added
explicit support for looking up custom fields.  Whereas the normal
lookup will the specific keys that Bitwarden supports in the `bw
get`:

    lookup('bitwarden', 'Google', field=username)

...adding `custom_field=True` causes the lookup to be performed against
the list of custom fields:

    lookup('bitwarden', 'Google', field=mycustomfield, custom_field=true)

## Add support for the sync operation

The Bitwarden CLI operates by keeping a local cache of your
credentials. This means that if you have just modified an item through
the web ui (or mobile app), you may still be querying stale data when
querying Bitwarden through the CLI.  The `bw sync` command refreshes
the local cache.

You can add `sync=true` to the lookup to have Ansible run `bw sync`
before querying Bitwarden for data:

    lookup('bitwarden', 'Google', field=username, sync=true)

## Using the lookup module in practice

We're using [TripleO][] to deploy OpenStack. TripleO requires as input
to the deployment process a number of parameters, including various
credentials.  For example, to set the password that will be assigned
to the Keystone admin user, one would pass in a file that looks
something like:

    ---
    parameter_defaults:
      AdminPassword: "secret.password.goes.here"

Because our deployment configuration is public, we don't want to store
credentials there.  We've been copying around a credentials file that
lives outside the repository, but that's not a great solution.

Using the Bitwarden lookup module, we can replace the above with:

    ---
    parameter_defaults:
      AdminPassword: "{{ lookup('bitwarden', 'keystone admin') }}"

With this change, we can use Ansible to query Bitwarden to get the
Keystone admin password and generate as output a file with the
passwords included.

Using the custom field support, we can include metadata associated
with a credential in the same place as the credential itself.  To
configure access to a remote Ceph installation, we need to provide a
client key and cluster id. By putting the cluster id in a custom
field, we can do something like this:

    CephClientKey: "{{ lookup('bitwarden', 'ceph client key') }}"
    CephClusterFSID: "{{ ((lookup('bitwarden', 'ceph client key', field='clusterid', custom_field=true) }}"

[tripleo]: https://docs.openstack.org/tripleo-docs/latest/

## An example playbook

Before you can run a playbook making use of the Bitwarden lookup
module, you need to [install][] the Bitwarden CLI.  This is as simple
as grabbing an appropriate binary and dropping it somewhere in
your `$PATH`.  I've been doing this:

    $ curl -L 'https://vault.bitwarden.com/download/?app=cli&platform=linux' |
      funzip > $HOME/bin/bw
    $ chmod 755 $HOME/bin/bw

[install]: https://help.bitwarden.com/article/cli/#download--install

For the following example, assume that we have a template named
`no-passwords-here.yml` matching the earlier example:

    ---
    parameter_defaults:
      AdminPassword: "{{ lookup('bitwarden', 'keystone admin') }}"

We can generate a version of the file named `yes-passwords-here.yml`
that includes the actual passwords by running the following playbook:

    ---
    - hosts: localhost

      # we need to include the role in order to make the lookup plugin
      # available.
      roles:
        - ansible-modules-bitwarden

      tasks:
        - name: inject passwords into a file
          template:
            src: ./no-passwords-here.yml
            dest: ./yes-passwords-here.yml

To actually run the playbook, we need to be authenticated to Bitwarden
first.  That means:

1. Run `bw login` (or `bw unlock`) to log in and get a session key.
1. Set the `BW_SESSION` environment variable to this value.
1. Run the playbook.

The above tasks would look something like this:

    bash$ bw login
    ? Email address: lars@redhat.com
    ? Master password: [hidden]
    You are logged in!

    To unlock your vault, set your session key to the `BW_SESSION`
    environment variable. ex:
    $ export BW_SESSION="..."
    [...]
    bash$ export BW_SESSION="..."
    bash$ ansible-playbook inject-passwords.yml
