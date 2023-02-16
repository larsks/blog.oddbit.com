---
aliases:
- /2015/07/26/in-which-we-are-amazed-it-doesnt-all-fall-apart/
- /post/2015-07-26-in-which-we-are-amazed-it-doesnt-all-fall-apart
categories:
- tech
date: '2015-07-26'
tags:
- openstack
- rant
title: In which we are amazed it doesn't all fall apart
---

So, the Kilo release notes say:

    nova-manage migrate-flavor-data

But nova-manage says:

    nova-manage db migrate_flavor_data

But that says:

    Missing arguments: max_number

And the help says:

    usage: nova-manage db migrate_flavor_data [-h]
      [--max-number <number>]

Which indicates that --max-number is optional, but whatever, so you
try:

    nova-manage db migrate_flavor_data --max-number 100

And that says:

    Missing arguments: max_number

So just for kicks you try:

    nova-manage db migrate_flavor_data --max_number 100

And that says:

    nova-manage: error: unrecognized arguments: --max_number

So finally you try:

    nova-manage db migrate_flavor_data 100

And holy poorly implement client, Batman, it works.