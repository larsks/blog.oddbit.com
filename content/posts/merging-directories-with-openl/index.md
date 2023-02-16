---
aliases:
- /2010/02/16/merging-directories-with-openldap-meta/
- /post/2010-02-16-merging-directories-with-openldap-meta
categories:
- tech
date: '2010-02-16'
tags:
- meta
- proxy
- openldap
- active_directory
- ldap
title: Merging directories with OpenLDAP's Meta backend
---

This document provides an example of using OpenLDAP's meta backend to provide a unified view of two distinct LDAP directory trees. I was frustrated by the lack of simple examples available when I went looking for information on this topic, so this is my attempt to make life easier for the next person looking to do the same thing.

The particular use case that motiviated my interest in this topic was the need to configure web applications to (a) authenticate against an existing Active Directory server while (b) also allowing new accounts to be provisioned quickly and without granting any access in the AD environment. A complicating factor is that the group managing the AD server(s) was not the group implementing the web applications.

# Assumptions

I'm making several assumptions while writing this document:

  - You have root access on your system and are able to modify files in /etc/openldap and elsewhere on the filesystem.
  - You are somewhat familiar with LDAP.
  - You are somewhat familiar with OpenLDAP.

# Set up backend directories

## Configure slapd

We'll first create two "backend" LDAP directories. These will represent the directories you're trying to merge. For the purposes of this example we'll use the ldif backend, which stores data in LDIF format on the filesystem. This is great for testing (it's simple and easy to understand), but not so great for performance.

We define one backend like this in /etc/openldap/slapd-be-1.conf:
    
    
    database        ldif
    suffix          "ou=backend1"
    directory       "/var/lib/ldap/backend1"
    rootdn          "cn=ldif-admin,ou=backend1"
    rootpw          "LDIF"
    

And a second backend like this in /etc/openldap/slapd-be-2.conf:
    
    
    database        ldif
    suffix          "ou=backend2"
    directory       "/var/lib/ldap/backend2"
    rootdn          "cn=ldif-admin,ou=backend2"
    rootpw          "LDIF"
    

Now, we need to load these configs into the main slapd configuration file. Open slapd.conf, and look for the following comment:
    
    
    #######################################################################
    # ldbm and/or bdb database definitions
    #######################################################################
    

Remove anything below this comment and then add the following lines:
    
    
    include /etc/openldap/slapd-be-1.conf
    include /etc/openldap/slapd-be-2.conf
    

## Start up slapd

Start up your LDAP service:
    
    
    # slapd -f slapd.conf -h ldap://localhost/
    

And check to make sure it's running:
    
    
    # ps -fe | grep slapd
    root 15087 1 0 22:48 ? 00:00:00 slapd -f slapd.conf -h ldap://localhost/
    

## Populate backends with sample data

We need to populate the directories with something to query.

Put this in backend1.ldif:
    
    
    dn: ou=backend1
    objectClass: top
    objectClass: organizationalUnit
    ou: backend1
    
    dn: ou=people,ou=backend1
    objectClass: top
    objectClass: organizationalUnit
    ou: people
    
    dn: cn=user1,ou=people,ou=backend1
    objectClass: inetOrgPerson
    cn: user1
    givenName: user1
    sn: Somebodyson
    mail: user1@example.com
    

And this in backend2.ldif:
    
    
    dn: ou=backend2
    objectClass: top
    objectClass: organizationalUnit
    ou: backend2
    
    dn: ou=people,ou=backend2
    objectClass: top
    objectClass: organizationalUnit
    ou: people
    
    dn: cn=user2,ou=people,ou=backend2
    objectClass: inetOrgPerson
    cn: user2
    givenName: user2
    sn: Somebodyson
    mail: user2@example.com
    

And then load the data into the backends:
    
    
    ldapadd -x -H ldap://localhost -D cn=ldif-admin,ou=backend1 \
      -w LDIF -f backend1.ldif
    

And:
    
    
    ldapadd -x -H ldap://localhost -D cn=ldif-admin,ou=backend2 \
      -w LDIF -f backend2.ldif
    

You can verify that the data loaded correctly by issuing a query to the backends. E.g.:
    
    
    ldapsearch -x -H ldap://localhost -b ou=backend1 -LLL
    

This should give you something that looks very much like the contents of backend1.ldif. You can do the same thing for backend2.

# Set up meta database

We're now going to configure OpenLDAP's meta backend to merge the two directory trees. Complete documentation for the meta backend can be found in the [slapd-meta man page][1].

Put the following into a file called slapd-frontend.conf (we'll discuss the details in moment):
    
    
    database        meta
    suffix          "dc=example,dc=com"
    
    uri             "ldap://localhost/ou=backend1,dc=example,dc=com"
    suffixmassage   "ou=backend1,dc=example,dc=com" "ou=backend1"
    
    uri             "ldap://localhost/ou=backend2,dc=example,dc=com"
    suffixmassage   "ou=backend2,dc=example,dc=com" "ou=backend2"
    

And then add to slapd.conf:
    
    
    include /etc/openldap/slapd-frontend.conf
    

Restart slapd. Let's do a quick search to see exactly what we've accomplished:
    
    
    $ ldapsearch -x -H 'ldap://localhost/' \
      -b dc=example,dc=com objectclass=inetOrgPerson -LLL
    dn: cn=user1,ou=people,ou=backend1,dc=example,dc=com
    objectClass: inetOrgPerson
    cn: user1
    givenName: user1
    sn: Somebodyson
    mail: user1@example.com
    
    dn: cn=user2,ou=people,ou=backend2,dc=example,dc=com
    objectClass: inetOrgPerson
    cn: user2
    givenName: user2
    sn: Somebodyson
    mail: user2@example.com
    

As you can see from the output above, a single query is now returning results from both backends, merged into the dc=example,dc=com hierarchy.

## A closer look

Let's take a closer look at the meta backend configuration.
    
    
    database        meta
    suffix          "dc=example,dc=com"
    

The database statement begins a new database definition. The suffix statement identifies the namespace that will be served by this particular database.

Here is the proxy for backend1 (the entry for backend2 is virtually identical):
    
    
    uri             "ldap://localhost/ou=backend1,dc=example,dc=com"
    suffixmassage   "ou=backend1,dc=example,dc=com" "ou=backend1"
    

The uri statement defines the host (and port) serving the target directory tree. The full syntax of the uri statement is described in the [slapd-meta man page][1]; what we have here is a very simple example. The _naming context_ of the URI must fall within the namespace defined in the suffix statement at the beginning of the database definition.

The suffixmassage statement performs simple rewriting on distinguished names. It directs _slapd_ to replace ou=backend1,dc=example,dc=com with ou=backend1 when communicating with the backend directory (and vice-versa).

You can perform simple rewriting of attribute and object classes with the map statement. For example, if backend1 used a sAMAccountName attribute and our application was expecting a uid attribute, we could add this after the suffixmassage statement:
    
    
    map attribute uid sAMAccountName
    

# Conclusion

The sample configuration files, data, and code referenced in this post are available online in [a github repository][2]:

> [http://github.com/larsks/OpenLDAP-Metadirectory-Example][2]

I hope you've found this post useful, or at least informative. If you have any comments or questions regarding this post, please log them as issues on GitHub. This will make them easier for me to track.

[1]: http://www.openldap.org/software/man.cgi?query=slapd-meta&apropos=0&sektion=0&manpath=OpenLDAP+2.4-Release&format=html
[2]: http://github.com/larsks/OpenLDAP-Metadirectory-Example