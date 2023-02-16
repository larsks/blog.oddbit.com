---
aliases:
- /2017/08/02/ansible-for-infrastructure-testing/
- /post/2017-08-02-ansible-for-infrastructure-testing
categories:
- tech
date: '2017-08-02'
tags:
- ansible
- ansible-assertive
- openstack
title: Ansible for Infrastructure Testing
---

At `$JOB` we often find ourselves at customer sites where we see the
same set of basic problems that we have previously encountered
elsewhere ("your clocks aren't in sync" or "your filesystem is full"
or "you haven't installed a critical update", etc). We would like a
simple tool that could be run either by the customer or by our own
engineers to test for and report on these common issues.
Fundamentally, we want something that acts like a typical code test
suite, but for infrastructure.

It turns out that Ansible is *almost* the right tool for the job:

- It's easy to write simple tests.
- It works well in distributed environments.
- It's easy to extend with custom modules and plugins.

The only real problem is that Ansible has, by default, "fail fast"
behavior: once a task fails on a host, no more tasks will run on that
host.  That's great if you're actually making configuration changes,
but for our purposes we are running a set of read-only independent
checks, and we want to know the success or failure of all of those
checks in a single operation (and in many situations we may not have
the option of correcting the underlying problem ourselves).

In this post, I would like to discuss a few Ansible extensions I've
put together to make it more useful as an infrastructure testing tool.

## The ansible-assertive project

The [ansible-assertive][] project contains two extensions for Ansible:

- The `assert` action plugin replaces Ansible's native `assert`
  behavior with something more appropriate for infrastructure testing.

- The `assertive` callback plugin modifies the output of `assert`
  tasks and collects and reports results.

[ansible-assertive]: https://github.com/larsks/ansible-assertive/

The idea is that you write all of your tests using the `assert`
plugin, which means you can run your playbooks in a stock environment
and see the standard Ansible fail-fast behavior, or you can activate
the `assert` plugin from the ansible-assertive project and get
behavior more useful for infrastructure testing.

## A simple example

Ansible's native `assert` plugin will trigger a task failure when an
assertion evaluates to `false`.  Consider the following example:

```yaml
- hosts: localhost
  vars:
    fruits:
      - oranges
      - lemons
  tasks:
    - assert:
        that: >-
          'apples' in fruits
        msg: you have no apples

    - assert:
        that: >-
          'lemons' in fruits
        msg: you have no lemons
```

If we run this in a stock Ansible environment, we will see the
following:

```
PLAY [localhost] ***************************************************************

TASK [Gathering Facts] *********************************************************
ok: [localhost]

TASK [assert] ******************************************************************
fatal: [localhost]: FAILED! => {
    "assertion": "'apples' in fruits",
    "changed": false,
    "evaluated_to": false,
    "failed": true,
    "msg": "you have no apples"
}
	to retry, use: --limit @/home/lars/projects/ansible-assertive/examples/ex-005/playbook1.retry

PLAY RECAP *********************************************************************
localhost                  : ok=1    changed=0    unreachable=0    failed=1
```

## A modified assert plugin

Let's activate the `assert` plugin in [ansible-assertive][].  We'll
start by cloning the project into our local directory:

    $ git clone https://github.com/larsks/ansible-assertive

And we'll activate the plugin by creating an `ansible.cfg` file with
the following content:

    [defaults]
    action_plugins = ./ansible-assertive/action_plugins

Now when we re-run the playbook we see that a failed assertion now
registers as `changed` rather than `failed`:

```
PLAY [localhost] ***************************************************************

TASK [Gathering Facts] *********************************************************
ok: [localhost]

TASK [assert] ******************************************************************
changed: [localhost]

TASK [assert] ******************************************************************
ok: [localhost]

PLAY RECAP *********************************************************************
localhost                  : ok=3    changed=1    unreachable=0    failed=0
```

While that doesn't look like much of a change, there are two things of
interest going on here.  The first is that the `assert` plugin
provides detailed information about the assertions specified in the
task; if we were to `register` the result of the failed assertion and
display it in a `debug` task, it would look like:

```
TASK [debug] *******************************************************************
ok: [localhost] => {
    "apples": {
        "ansible_stats": {
            "aggregate": true,
            "data": {
                "assertions": 1,
                "assertions_failed": 1,
                "assertions_passed": 0
            },
            "per_host": true
        },
        "assertions": [
            {
                "assertion": "'apples' in fruits",
                "evaluated_to": false
            }
        ],
        "changed": true,
        "failed": false,
        "msg": "you have no apples"
    }
}
```

The `assertions` key in the result dictionary contains of a list of
tests and their results.  The `ansible_stats` key contains metadata
that will be consumed by the custom statistics support in recent
versions of Ansible.  If you have Ansible 2.3.0.0 or later, add
the following to the `defaults` section of your `ansible.cfg`:

```
show_custom_stats = yes
```

With this feature enabled, your playbook run will conclude with:

```
CUSTOM STATS: ******************************************************************
	localhost: { "assertions": 2,  "assertions_failed": 1,  "assertions_passed": 1}
```

## A callback plugin for better output

The `assertive` callback plugin provided by the [ansible-assertive][]
project will provide more useful output concerning the result of
failed assertions.  We activate it by adding the following to our
`ansible.cfg`:

    callback_plugins = ./ansible-assertive/callback_plugins
    stdout_callback = assertive

Now when we run our playbook we see:

```
PLAY [localhost] ***************************************************************

TASK [Gathering Facts] *********************************************************
ok: [localhost]

TASK [assert] ******************************************************************
failed: [localhost]  ASSERT('apples' in fruits)
failed: you have no apples

TASK [assert] ******************************************************************
passed: [localhost]  ASSERT('lemons' in fruits)

PLAY RECAP *********************************************************************
localhost                  : ok=3    changed=1    unreachable=0    failed=0
```

## Machine readable statistics

The above is nice but is still primarily human-consumable.  What if we
want to collect test statistics for machine processing (maybe we want
to produce a nicely formatted report of some kind, or maybe we want to
aggregate information from multiple test runs, or maybe we want to
trigger some action in the event there are failed tests, or...)?  You
can ask the `assertive` plugin to write a YAML format document with
this information by adding the following to your `ansible.cfg`:

    [assertive]
    results = testresult.yml

After running our playbook, this file would contain:

```yaml
groups:
- hosts:
    localhost:
      stats:
        assertions: 2
        assertions_failed: 1
        assertions_passed: 1
        assertions_skipped: 0
      tests:
      - assertions:
        - test: '''apples'' in fruits'
          testresult: failed
        msg: you have no apples
        testresult: failed
        testtime: '2017-08-04T21:20:58.624789'
      - assertions:
        - test: '''lemons'' in fruits'
          testresult: passed
        msg: All assertions passed
        testresult: passed
        testtime: '2017-08-04T21:20:58.669144'
  name: localhost
  stats:
    assertions: 2
    assertions_failed: 1
    assertions_passed: 1
    assertions_skipped: 0
stats:
  assertions: 2
  assertions_failed: 1
  assertions_passed: 1
  assertions_skipped: 0
timing:
  test_finished_at: '2017-08-04T21:20:58.670802'
  test_started_at: '2017-08-04T21:20:57.918412'
```

With these tools it becomes much easier to design playbooks for
testing your infrastructure.