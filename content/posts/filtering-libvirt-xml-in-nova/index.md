---
categories: [tech]
aliases: ["/2015/02/05/filtering-libvirt-xml-in-nova/"]
title: Filtering libvirt XML in Nova
date: "2015-02-05"
tags:
  - openstack
  - nova
---

I saw a request from a customer float by the other day regarding the
ability to filter the XML used to create Nova instances in libvirt.
The customer effectively wanted to blacklist a variety of devices (and
device types).  The consensus seems to be "you can't do this right now
and upstream is unlikely to accept patches that implement this
behavior", but it sounded like an interesting problem, so...

- <https://github.com/larsks/nova/tree/feature/xmlfilter>

This is a fork of Nova (Juno) that includes support for an extensible
filtering mechanism that is applied to the generated XML before it
gets passed to libvirt.

## How it works

The code uses the [stevedore][] module to handle locating and loading
filters.  A filter is a Python class that implements a `filter`
method with the following signature:

[stevedore]: https://github.com/dreamhost/stevedore

    def filter(self, xml, instance=None, context=None)

The code in `nova.virt.libvirt.domxmlfilters` collects all filters
registered in the `nova.filters.domxml` namespace, and then runs them
in sequence, passing the output of one filter as the output to the
next:

    filters = stevedore.extension.ExtensionManager(
        'nova.filters.domxml',
        invoke_on_load=True,
    )


    def filter_domain_xml(xml,
                          instance=None,
                          context=None):

        '''Filter the XML content in 'xml' through any filters registered in
        the nova.filters.domxml namespace.'''

        revised = xml
        for filter in filters:
            LOG.debug('filtering xml with filter %s',
                      filter.name)
            revised = filter.obj.filter(revised,
                                        instance=instance,
                                        context=context
                                        )

        return revised

The filters are called from the `_get_guest_xml` method in
`nova/virt/libvirt/driver.py`.

## An example filter

This filter will add an interface to the libvirt `default` network to
any instance created by Nova:

    from lxml import etree


    class AddNetworkFilter (object):
        def filter(self, xml,
                   instance=None,
                   context=None):

            doc = etree.fromstring(xml)

            network = etree.fromstring('''
            <interface type="network">
              <source network="default"/>
              <model type="virtio"/>
            </interface>
            ''')

            devices = doc.xpath('/domain/devices')[0]
            devices.append(network)

            return etree.tostring(doc, pretty_print=True)

You can find this in my [demo_nova_filters][] repository, along with a
few other trivial examples.  The above filter is registered via the
`entry_points` section of the `setup.py` file:

[demo_nova_filters]: https://github.com/larsks/demo_nova_filters/

    #!/usr/bin/env python

    import setuptools

    setuptools.setup(
        name="demo_nova_filters",
        version=1,
        packages=['demo_nova_filters'],
        entry_points={
            'nova.filters.domxml': [
                'prettyprint=demo_nova_filters.prettyprint:PrettyPrintFilter',
                'novideo=demo_nova_filters.novideo:NoVideoFilter',
                'addnetwork=demo_nova_filters.addnetwork:AddNetworkFilter',
            ]
        },
    )

And that's it.  This is almost entirely untested.  While it works in
some cases it doesn't work in all cases, and it's unlikely that I'm
going to update this to work with any future version of Nova.  This
was really just an exercise in curiosity.  Enjoy!

