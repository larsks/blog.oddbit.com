---
aliases:
- /2015/07/16/mapping-local-users-to-kerberos-principals-with-sssd/
- /post/2015-07-16-mapping-local-users-to-kerberos-principals-with-sssd
categories:
- tech
date: '2015-07-16'
tags:
- sssd
- kerberos
title: Mapping local users to Kerberos principals with SSSD
---

I work for an organization that follows the common model of assigning
people systematically generated user ids.  Like most technically
inclined employees of this organization, I have local accounts on my
workstation that don't bear any relation to the generated account ids.
For the most part this isn't a problem, except that our organization
uses Kerberos to authenticate access to a variety of resources (such
as the mailserver and a variety of web applications).

In the past, I've gotten along by running an explicit `kinit
lkellogg@EXAMPLE.COM` on the command line once in a while, and that
works, but it's not particularly graceful.

I'm running Fedora, which of course ships with [SSSD][].  Two of the
neat features available through SSSD are (a) you can have it acquire a
token for you automatically when you authenticate and (b) renew that
token periodically, assuming that you have a renewable token.

There are two problems that were preventing me from taking advantage
of this service.

[sssd]: https://fedorahosted.org/sssd/

## Combining Kerberos with local accounts

The first problem is that there is a general assumption that if you're
using Kerberos for authentication, you are also using some sort of
enterprise-wide identity service like LDAP.  The practical evidence of
this in SSSD is that you can't use Kerberos as an `auth_provider` if
you are using the `local` `id_provider`.  If you attempt a naive
configuration that includes the following:

    [domain/local]
    id_provider = local
    auth_provider = krb5

You'll get:

    (Thu Jul 16 22:19:44:802460 2015) [sssd] [confdb_get_domain_internal]
    (0x0010): Local ID provider does not support [krb5] as an AUTH provider.

It turns out that you can work around this limitation with a "proxy"
identity provider.  With this method, SSSD *proxies* identity requests
to an existing NSS library.  This can, for example, be used to get
SSSD to interoperate with a legacy NIS environment, as in [this
example][]:

[this example]: http://docs.fedoraproject.org/en-US/Fedora/15/html/Deployment_Guide/sect-SSSD_User_Guide-Domain_Configuration_Options-Configuring_a_Proxy_Domain.html#sect-SSSD-proxy-krb5

    [domain/PROXY_KRB5]
    auth_provider = krb5
    krb5_server = 192.168.1.1
    krb5_realm = EXAMPLE.COM

    id_provider = proxy
    proxy_lib_name = nis
    enumerate = true
    cache_credentials = true

The `proxy_lib_name` setting identifies the particular NSS provider to
use for identity information.  This would make use of the `nis` NSS
module (`libnss_nis.so.2`) for identity information while using
Kerberos for authentication.

For my own use case I want to use my local accounts for identity
information, which means I need to use the `files` NSS provider:

    [domain/example.com]
    id_provider = proxy
    proxy_lib_name = files
    auth_provider = krb5

## Mapping a local username to a Kerberos principal

The second problem I had been struggling with was how to map my local
username (`lars`) to the organizational Kerberos principal
(`lkellogg@EXAMPLE.COM`).  I had originally been looking at solutions
involving `kinit`, but despite promising verbage in the
[k5identity(5][k5id] man page, I wasn't meeting with much success.

[k5id]: http://web.mit.edu/kerberos/krb5-1.12/doc/user/user_config/k5identity.html

It turns out that SSSD has the `krb5_map_user` option for exactly this
purpose; the syntax looks like:

    krb5_map_user = <local name>:<principal name>

So, for me:

    krb5_map_user = lars:lkellogg

## Automatic ticket renewal

SSSD is able to automatically renew your Kerberos tickets for you,
provided that you're able to acquire a renewable ticket.  You can
check for this by running `klist` and seeing if your ticket has a
`renew until` date in the future, as in the following example:

    Ticket cache: KEYRING:persistent:1000:krb_ccache_rOS6mR8
    Default principal: lkellogg@REDHAT.COM

    Valid starting       Expires              Service principal
    07/17/2015 11:02:31  07/17/2015 21:02:31  krbtgt/REDHAT.COM@REDHAT.COM
      renew until 07/24/2015 11:02:31

If you meet this criteria, then you can add the following
configuration options to your domain configuration:

    krb5_renewable_lifetime = 7d
    krb5_renew_interval = 30m

The first (`krb5_renewable_lifetime`) specifies the renewable lifetime
to request when requesting a ticket, and the second (`krb5_renew_interval`) indicates how often SSSD should check to see if the ticket should be renewed.

## An example configuration

This is approximately (names of been changed to protect the innocent)
configuration that I am currently using with SSSD:

    [domain/default]
    cache_credentials = True

    [sssd]
    config_file_version = 2
    reconnection_retries = 3
    sbus_timeout = 30
    services = nss, pam
    domains = example.com

    [nss]
    filter_groups = root
    filter_users = root
    reconnection_retries = 3

    [pam]
    reconnection_retries = 3

    [domain/example.com]
    id_provider = proxy
    proxy_lib_name = files
    enumerate = True
    auth_provider = krb5
    krb5_server = kerberos.example.com
    krb5_realm = EXAMPLE.COM
    cache_credentials = True
    krb5_store_password_if_offline = True
    krb5_map_user = lars:lkellogg
    chpass_provider = krb5
    krb5_kpasswd = kerberos.example.com
    offline_credentials_expiration = 0
    krb5_renewable_lifetime = 7d
    krb5_renew_interval = 30m

## Configuring PAM

You're not done yet!  Once you have SSSD configured correctly, you
need to configure your system to make use of it for authentication.
First, you'll want to ensure that your `/etc/nsswitch.conf` file is
configured to use SSSD.  You'll want at least the `passwd`, `shadow`,
and `group` databases configured to use SSSD:

    passwd:     files sss
    shadow:     files sss
    group:      files sss

Next, you'll want configure PAM.  On my system, I need to change two
configuration files:

- `/etc/pam.d/system-auth`, which is the default for many services,
  and
- `/etc/pam.d/password-auth`, which provides defaults for other
  services, including `sshd`.

In my case, both files actually end up having identical content, which
looks like this (largely cribbed from [the Fedora documentation][docs]):

[docs]: http://docs.fedoraproject.org/en-US/Fedora/15/html/Deployment_Guide/chap-SSSD_User_Guide-Setting_Up_SSSD.html

    #%PAM-1.0
    # This file is auto-generated.
    # User changes will be destroyed the next time authconfig is run.
    auth        required      pam_env.so
    auth        sufficient    pam_unix.so nullok try_first_pass
    auth        requisite     pam_succeed_if.so uid >= 1000 quiet_success
    auth        sufficient    pam_sss.so use_first_pass
    auth        required      pam_deny.so

    account     required      pam_unix.so
    account     sufficient    pam_localuser.so
    account     sufficient    pam_succeed_if.so uid < 1000 quiet
    account     [default=bad success=ok user_unknown=ignore] pam_sss.so
    account     required      pam_permit.so

    password    requisite     pam_pwquality.so try_first_pass local_users_only retry=3 authtok_type=
    password    sufficient    pam_unix.so sha512 shadow nullok try_first_pass use_authtok
    password    sufficient    pam_sss.so use_authtok
    password    required      pam_deny.so

    session     optional      pam_keyinit.so revoke
    session     required      pam_limits.so
    -session     optional      pam_systemd.so
    session     [success=1 default=ignore] pam_succeed_if.so service in crond quiet use_uid
    session     optional      pam_sss.so
    session     required      pam_unix.so

Note the entries for `pam_sss.so` in each stanza.

## The proof in the pudding

I start on my local system with no Kerberos tickets:

    $ klist
    klist: Credentials cache keyring 'persistent:1000:krb_ccache_Pzo4C6u' not found

Then I lock my screen and unlock it using my Kerberos password, and
now:

    $ klist
    Ticket cache: KEYRING:persistent:1000:krb_ccache_rOS6mR8
    Default principal: lkellogg@EXAMPLE.COM

    Valid starting       Expires              Service principal
    07/16/2015 22:45:43  07/17/2015 08:45:43  krbtgt/EXAMPLE.COM@EXAMPLE.COM
      renew until 07/23/2015 22:45:43

## Troubleshooting

I found the easiest way to troubleshoot SSSD was to stop the service:

    # systemctl stop sssd

And then run `sssd` on the command line in debug mode:

    # sssd -d 5 -i

This generates logs on `stderr` and helped me identity problems in my
configuration.

## Kudos

Thanks to Jakub Hrozek for suggesting the use of the a proxy identity
provider to overcome the limitation on combining Kerberos with the
`local` provider.