---
categories: [tech]
aliases: ["/2013/07/22/generating-a-membero/"]
title: Generating a memberOf attribute for posixGroups
date: "2013-07-22"
tags:
  - ldap
---

This showed up on [#openstack][] earlier today:

    2013-07-22T13:56:10  <m0zes> hello, all. I am looking to
    setup keystone with an ldap backend. I need to filter
    users based on group membership, in this case a
    non-rfc2307 posixGroup. This means that memberOf doesn't
    show up, and that the memberUid in the group is not a
    dn. any thoughts on how to accomplish this?

It turns out that this is a not uncommon question, so I spent some
time today working out a solution using the [dynlist][] overlay for
[OpenLDAP][].

<!-- more -->

The LDIF data presented in this article can be found [on github][].

[on github]: https://github.com/larsks/blog-openldap-dynlist

Assumptions
-----------

I'm assuming that you have a traditional `posixGroup` that looks
something like this:

    dn: cn=lars,ou=groups,dc=oddbit,dc=com
    objectClass: posixGroup
    cn: lars
    gidNumber: 1000
    memberUid: lars

That is, members are recorded in the `memberUid` attribute which
corresponds to the `uidNumber` attribute of a user object.

Loading the dynlist module
--------------------------

This solution makes use of the `dynlist` dynamic overlay, so you'll
first need to make sure that module is loaded.  Most modern OpenLDAP
deployments make use of the new `slapd.d` configuration directory,
which means you'll modify your configuration by loading the following
LDIF file:

    dn: cn=modules,cn=config
    objectClass: olcModuleList
    cn: modules
    olcModuleLoad: dynlist

You would load this into your running instance with something like the
following:

    # ldapadd -Y EXTERNAL -H ldapi://%2fvar%2frun%2fldapi -f dynlist.ldif

This makes certain assumptions about how your permissions are
configured (in particular, it assumes that your server is configured
to permit administrative access to system UID 0 when accessing the
`ldapi` socket).

If you already have a `cn=modules{0},cn=config` object, you'll need to
modify instead using the following:

    dn: cn=modules,cn=config
    changetype: modify
    add: olcModuleLoad
    olcModuleLoad: dynlist

And use `ldapmodify`:

    # ldapmodify -Y EXTERNAL -H ldapi://%2fvar%2frun%2fldapi -f dynlist.ldif

Schema modifications
----------------------

In an ideal world, we would be able to make our solution populate the
standard `memberOf` attribute.  Unfortunately, this is an
"operational" attribute in OpenLDAP, which means we can't make it
available to a user class...so, we're going to define (a) a new
`attributeType` that is largely identical to the `memberOf` attribute,
and (b) a new auxiliary object class that allows the new attribute.

    dn: cn=oddbit,cn=schema,cn=config
    objectClass: olcSchemaConfig
    cn: oddbit
    olcAttributeTypes: ( 1.3.6.1.4.1.24441.1.1.1 
     NAME 'obMemberOf' 
     DESC 'Distinguished name of a group of which the object is a member' 
     EQUALITY distinguishedNameMatch 
     SYNTAX 1.3.6.1.4.1.1466.115.121.1.12 )
    olcObjectClasses: ( 1.3.6.1.4.1.24441.2.1.1 
     NAME 'obPerson' DESC 'oddbit.com person' 
     AUXILIARY MAY ( obMemberOf ) )

This gives us the `obMemberOf` attribute and the `obPerson` object
class.  **NOTE**: the OIDs I'm using here are using my own
IANA-assigned OID prefix.  You should replace `1.3.6.1.4.1.24441` with
your own OID prefix.  If you don't have one (and you're sure your
organization doesn't already have one), you can [register][] for your
own.

Defining a dynamic list
-----------------------

We're going to configure the `dynlist` overlay so that when it sees an
`obPerson` object, it will use the `labeledURI` attribute of that
object to generate a list of `obMemberOf` attributes containing the
distinguished names of the groups of which the user is a member.
We'll load the following LDIF file into our server:

    dn: olcOverlay=dynlist,olcDatabase={2}hdb,cn=config
    objectClass: olcOverlayConfig
    objectClass: olcDynamicList
    olcOverlay: dynlist
    olcDlAttrSet: obPerson labeledURI obMemberOf

Note that the distinguished name for this entry depends on the DN of
the database which you are configuring, so you'll need to modify the
`olcDatabase=` component in the DN.

Setting user attributes
-----------------------

With the above configuration in place, we can now add the necessary
`labeledURI` attribute to a user and see what happens.  For our
purposes, this attribute needs to contain an LDAP URI that returns the
groups of which the user is a member.  Assuming a user like this:

    dn: cn=user1,ou=people,dc=oddbit,dc=com
    objectClass: posixAccount
    objectClass: inetOrgPerson
    cn: user1
    sn: testuser
    uid: user1
    uidNumber: 1001
    gidNumber: 1001
    homeDirectory: /home/user1

We'll need to add the following:

    labeledURI: ldap:///ou=groups,dc=oddbit,dc=com??sub?(&(
     objectclass=posixgroup)(memberuid=user1))

You could do this with the following LDIF file and `ldapmodify`:

    dn: cn=user1,ou=people,dc=oddbit,dc=com
    changetype: modify
    add: labeledURI
    labeledURI: ldap:///ou=groups,dc=oddbit,dc=com??sub?(&(
     objectclass=posixgroup)(memberuid=user1))

Testing things out
------------------

Assuming we have the following groups:

    dn: cn=user1,ou=groups,dc=oddbit,dc=com
    objectClass: posixGroup
    cn: user1
    gidNumber: 1001
    memberUid: lars
    memberUid: user1

    dn: cn=staff,ou=groups,dc=oddbit,dc=com
    objectClass: posixGroup
    cn: staff
    gidNumber: 2000
    memberUid: user1

If we look up the `user1` user:

    # ldapsearch -Y EXTERNAL -H ldapi://%2fvar%2frun%2fldapi -b \
      ou=people,dc=oddbit,dc=com cn=user1

We should see `obMemberOf` attributes in the result:

    dn: cn=user1,ou=people,dc=oddbit,dc=com
    cn: user1
    sn: testuser
    uid: user1
    uidNumber: 1001
    gidNumber: 1001
    homeDirectory: /home/user1
    labeledURI: ldap:///ou=groups,dc=oddbit,dc=com??sub?(&(objectclass=posixgroup)
     (memberuid=user1))
    objectClass: inetOrgPerson
    objectClass: obPerson
    objectClass: posixAccount
    obmemberof: cn=user1,ou=groups,dc=oddbit,dc=com
    obmemberof: cn=staff,ou=groups,dc=oddbit,dc=com

Caveats
-------

Note that this solution requires searching through all of your group
entries every time you look up a user object.  Given a sufficiently
large directory this may not be an optimal solution.

[openldap]: http://www.openldap.org/
[dynlist]: http://www.openldap.org/faq/data/cache/1209.html
[register]: http://pen.iana.org/pen/PenApplication.page
[#openstack]: https://wiki.openstack.org/wiki/IRC

