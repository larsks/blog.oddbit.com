---
categories: [tech]
aliases: ["/2014/09/27/integrating-custom-code-with-n/"]
title: Integrating custom code with Nova using hooks
date: "2014-09-27"
tags:
  - openstack
  - nova
---

Would you like to run some custom Python code when Nova creates and
destroys virtual instances on your compute hosts?  This is possible
using Nova's support for [hooks][], but the existing documentation is
somewhat short on examples, so I've spent some time trying to get
things working.

[hooks]: http://docs.openstack.org/developer/nova/devref/hooks.html

The [demo_nova_hooks][] repository contains a working example of the
techniques discussed in this article.

[demo_nova_hooks]: https://github.com/larsks/demo_nova_hooks

## What's a hook?

A Nova "hook" is a mechanism that allows you to attach a class of your
own design to a particular function or method call in Nova.  Your
class should define a `pre` method (that will be called before the
method is called) and `post` function (that will be called after the
method is called):

    class YourHookClass(object):

        def pre(self, *args, **kwargs):
            ....

        def post(self, rv, *args, **kwargs):
            ....

The `pre` method will be called with the positional and keyword
arguments being passed to the hooked function.  The `post` method
receives the return value of the called method in addition to the
positional and keyword arguments.

You connect your code to available hooks using [Setuptools entry
points][ep].  For example, assuming that the above code lived in
module named `your_package.hooks`, you might have the following in the
corresponding `setup.py` file:

[ep]: https://pythonhosted.org/setuptools/setuptools.html

    entry_points = {
        'nova.hooks': [
          'create_instance=your_package.hooks:YourHookClass',
        ]
    },

## What hooks are available?

The Nova code (as of [81b1bab][]) defines three hooks:

[81b1bab]: https://github.com/openstack/nova/commit/81b1babcd9699118f57d5055ff9045e275b536b5

- `create_instance`
- `delete_instances`
- `instance_network_info`

### create_instance

The `create_instance` hook is attached to the Nova API `create`
function, and will receive the following arguments:

    def create(self, context, instance_type,
               image_href, kernel_id=None, ramdisk_id=None,
               min_count=None, max_count=None,
               display_name=None, display_description=None,
               key_name=None, key_data=None, security_group=None,
               availability_zone=None, user_data=None, metadata=None,
               injected_files=None, admin_password=None,
               block_device_mapping=None, access_ip_v4=None,
               access_ip_v6=None, requested_networks=None, config_drive=None,
               auto_disk_config=None, scheduler_hints=None, legacy_bdm=True,
               shutdown_terminate=False, check_server_group_quota=False):

When called, `self` is a `nova.compute.api.API` object, `context` is a
`nova.context.RequestContext` object, `instance_type` is a dictionary
containing information about the selected flavor, and `image_href` is
an image UUID.

During my testing, the `instance_type` dictionary looked like this...

    {'created_at': None,
     'deleted': 0L,
     'deleted_at': None,
     'disabled': False,
     'ephemeral_gb': 0L,
     'extra_specs': {},
     'flavorid': u'2',
     'id': 5L,
     'is_public': True,
     'memory_mb': 2048L,
     'name': u'm1.small',
     'root_gb': 20L,
     'rxtx_factor': 1.0,
     'swap': 0L,
     'updated_at': None,
     'vcpu_weight': None,
     'vcpus': 1L}

...corresponding to the `m1.small` flavor on my system.

### delete_instance

The `delete_instance` hook is attached to the `_delete_instance`
method in the `nova.compute.manager.ComputeManager` class, which is
called whenever Nova needs to delete an instance.  The hook will
receive the following arguments:

    def _delete_instance(self, context, instance, bdms, quotas):

Where:

- `self` is a `nova.compute.manager.ComputeManager` object,
- `context` is a `nova.context.RequestContext`, 
- `instance` is a `nova.objects.instance.Instance` object
- `bdms` is a `nova.objects.block_device.BlockDeviceMappingList`
  object, and
- `quotas` is a `nova.objects.quotas.Quotas` object

### instance_network_info

The `instance_network_info` hook is attached to the
`update_instance_cache_with_nw_info` function in
`nova.network.base_api.py`.  The hook will receive the following
arguments:

    def update_instance_cache_with_nw_info(impl, context, instance,
                                           nw_info=None, update_cells=True):

I am not running Nova Network in my environment, so I have not
examined this hook in any additional detail.

## A working example

The [demo_nova_hooks][] repository implements simple logging-only
implementations of `create_instance` and `delete_instance` hooks.  You
can install this code, restart Nova services, boot an instances, and
verify that the code has executed by looking at the logs generated in
`/var/log/nova`.
