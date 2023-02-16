---
categories: [tech]
aliases: ["/2010/02/02/nfs-and-16-group-limit/"]
title: NFS and the 16-group limit
date: "2010-02-02"
tags:
  - groups
  - nfs
---

I learned something new today: it appears that the underlying authorization mechanism used by NFS limits your group membership to 16 groups. From [http://bit.ly/cBhU8N][1]:

> NFS is built on ONC RPC (Sun RPC). NFS depends on RPC for authentication and identification of users. Most NFS deployments use an RPC authentication flavor called AUTH_SYS (originally called AUTH_UNIX, but renamed to AUTH_SYS).
> 
> AUTH_SYS sends 3 important things:
>
>>   - A 32 bit numeric user identifier (what you'd see in the UNIX /etc/passwd file)
>>   - A 32 bit primary numeric group identifier (ditto)
>>   - A variable length list of up to 16 32-bit numeric supplemental group identifiers (what'd you see in the /etc/group file)

We ran into this today while diagnosing a weird permissions issue. Who knew?

[1]: http://bit.ly/cBhU8N

