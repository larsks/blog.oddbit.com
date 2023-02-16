---
aliases:
- /2015/01/04/building-a-minimal-web-server-for-testing-kubernetes/
- /post/2015-01-04-building-a-minimal-web-server-for-testing-kubernetes
categories:
- tech
date: '2015-01-04'
tags:
- docker
- kubernetes
title: Building a minimal web server for testing Kubernetes
---

I have recently been doing some work with [Kubernetes][], and wanted
to put together a minimal image with which I could test service and
pod deployment.  Size in this case was critical: I wanted something
that would download quickly when initially deployed, because I am
often setting up and tearing down Kubernetes as part of my testing
(and some of my test environments have poor external bandwidth).

[kubernetes]: https://github.com/googlecloudplatform/kubernetes

## Building thttpd

My go-to minimal webserver is [thttpd][]. For the normal case,
building the software is a simple matter of `./configure` followed by
`make`.  This gets you a dynamically linked binary; using `ldd` you
could build a Docker image containing only the necessary shared
libraries:

[thttpd]: http://acme.com/software/thttpd/

    $ mkdir thttpd-root thttpd-root/lib64
    $ cp thttpd thttpd-root/
    $ cd thttpd-root
    $ cp $(ldd thttpd | awk '$3 ~ "/" {print $3}') lib64/
    $ cp /lib64/ld-linux-x86-64.so.2 lib64/

Which gets us:

    $ find * -type f
    lib64/ld-linux-x86-64.so.2
    lib64/libdl.so.2
    lib64/libc.so.6
    lib64/libcrypt.so.1
    lib64/libfreebl3.so
    thttpd

However, if we try to run `thttpd` via a `chroot` into this directory,
it will fail:

    $ sudo chroot $PWD /thttpd -D
    /thttpd: unknown user - 'nobody'

A little `strace` will show us what's going on:

    $ sudo strace chroot $PWD /thttpd -D
    [...]
    open("/etc/nsswitch.conf", O_RDONLY|O_CLOEXEC) = -1 ENOENT (No such file or directory)
    open("/lib64/libnss_compat.so.2", O_RDONLY|O_CLOEXEC) = -1 ENOENT (No such file or directory)
    [...]    

It's looking for an [NSS][] configuration and related libraries.  So
let's give it what it wants:

[nss]: https://en.wikipedia.org/wiki/Name_Service_Switch

    $ mkdir etc
    $ cat > etc/nsswitch.conf <<EOF
    passwd: files
    group: files
    EOF
    $ grep nobody /etc/passwd > etc/passwd
    $ grep nobody /etc/group > etc/group
    $ cp /lib64/libnss_files.so.2 lib64/

And now:

    $ sudo chroot $PWD /thttpd -D

...and it keeps running.  This gives a filesystem that is almost
exactly 3MB in size. Can we do better?

## Building a static binary

In theory, building a static binary should be as simple as:

    $ make CCOPT='-O2 -static'

But on my Fedora 21 system, this gets me several warnings:

    thttpd.c:(.text.startup+0xf81): warning: Using 'initgroups' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
    thttpd.c:(.text.startup+0x146d): warning: Using 'getpwnam' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
    thttpd.c:(.text.startup+0x65d): warning: Using 'getaddrinfo' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking

And then a bunch of errors:

    /usr/lib/gcc/x86_64-redhat-linux/4.9.2/../../../../lib64/libcrypt.a(md5-crypt.o): In function `__md5_crypt_r':
    (.text+0x11c): undefined reference to `NSSLOW_Init'
    /usr/lib/gcc/x86_64-redhat-linux/4.9.2/../../../../lib64/libcrypt.a(md5-crypt.o): In function `__md5_crypt_r':
    (.text+0x136): undefined reference to `NSSLOWHASH_NewContext'
    /usr/lib/gcc/x86_64-redhat-linux/4.9.2/../../../../lib64/libcrypt.a(md5-crypt.o): In function `__md5_crypt_r':
    (.text+0x14a): undefined reference to `NSSLOWHASH_Begin'
    /usr/lib/gcc/x86_64-redhat-linux/4.9.2/../../../../lib64/libcrypt.a(md5-crypt.o): In function `__md5_crypt_r':
    [...]

Fortunately (?), this is a distribution-specific problem.  Building
`thttpd` inside an Ubuntu Docker container seems to work fine:

    $ docker run -it --rm -v $PWD:/src ubuntu
    root@1e126269241c:/# apt-get update; apt-get -y install make gcc
    root@1e126269241c:/# make -C /src CCOPT='-O2 -static'
    root@1e126269241c:/# exit

Now we have a statically built binary:

    $ file thttpd
    thttpd: ELF 64-bit LSB executable, x86-64, version 1 (GNU/Linux), statically linked, for GNU/Linux 2.6.24, BuildID[sha1]=bb211a88e9e1d51fa2e937b2b7ea892d87a287d5, not stripped

Let's rebuild our `chroot` environment:

    $ rm -rf thttpd-root
    $ mkdir thttpd-root thttpd-root/lib64
    $ cp thttpd thttpd-root/
    $ cd thttpd-root

And try running `thttpd` again:

    $ sudo chroot $PWD /thttpd -D
    /thttpd: unknown user - 'nobody'

Bummer.  It looks like the NSS libraries are still biting us, and it
looks as if statically compiling code that uses NSS [may be tricky][].
Fortunately, it's relatively simple to patch out the parts of the
`thttpd` code that are trying to switch to another uid/gid.  The
following [patch][] will do the trick:

[may be tricky]: https://stackoverflow.com/questions/3430400/linux-static-linking-is-dead
[patch]: https://github.com/larsks/docker-image-thttpd/blob/master/builder/thttpd-runasroot.patch

    diff --git a/thttpd.c b/thttpd.c
    index fe21b44..397feb1 100644
    --- a/thttpd.c
    +++ b/thttpd.c
    @@ -400,22 +400,6 @@ main( int argc, char** argv )
         if ( throttlefile != (char*) 0 )
      read_throttlefile( throttlefile );
     
    -    /* If we're root and we're going to become another user, get the uid/gid
    -    ** now.
    -    */
    -    if ( getuid() == 0 )
    -	{
    -	pwd = getpwnam( user );
    -	if ( pwd == (struct passwd*) 0 )
    -	    {
    -	    syslog( LOG_CRIT, "unknown user - '%.80s'", user );
    -	    (void) fprintf( stderr, "%s: unknown user - '%s'\n", argv0, user );
    -	    exit( 1 );
    -	    }
    -	uid = pwd->pw_uid;
    -	gid = pwd->pw_gid;
    -	}
    -
         /* Log file. */
         if ( logfile != (char*) 0 )
      {
    @@ -441,17 +425,6 @@ main( int argc, char** argv )
        (void) fprintf( stderr, "%s: logfile is not an absolute path, you may not be able to re-open it\n", argv0 );
        }
          (void) fcntl( fileno( logfp ), F_SETFD, 1 );
    -	    if ( getuid() == 0 )
    -		{
    -		/* If we are root then we chown the log file to the user we'll
    -		** be switching to.
    -		*/
    -		if ( fchown( fileno( logfp ), uid, gid ) < 0 )
    -		    {
    -		    syslog( LOG_WARNING, "fchown logfile - %m" );
    -		    perror( "fchown logfile" );
    -		    }
    -		}
          }
      }
         else
    @@ -680,41 +653,6 @@ main( int argc, char** argv )
         stats_bytes = 0;
         stats_simultaneous = 0;
     
    -    /* If we're root, try to become someone else. */
    -    if ( getuid() == 0 )
    -	{
    -	/* Set aux groups to null. */
    -	if ( setgroups( 0, (const gid_t*) 0 ) < 0 )
    -	    {
    -	    syslog( LOG_CRIT, "setgroups - %m" );
    -	    exit( 1 );
    -	    }
    -	/* Set primary group. */
    -	if ( setgid( gid ) < 0 )
    -	    {
    -	    syslog( LOG_CRIT, "setgid - %m" );
    -	    exit( 1 );
    -	    }
    -	/* Try setting aux groups correctly - not critical if this fails. */
    -	if ( initgroups( user, gid ) < 0 )
    -	    syslog( LOG_WARNING, "initgroups - %m" );
    -#ifdef HAVE_SETLOGIN
    -	/* Set login name. */
    -        (void) setlogin( user );
    -#endif /* HAVE_SETLOGIN */
    -	/* Set uid. */
    -	if ( setuid( uid ) < 0 )
    -	    {
    -	    syslog( LOG_CRIT, "setuid - %m" );
    -	    exit( 1 );
    -	    }
    -	/* Check for unnecessary security exposure. */
    -	if ( ! do_chroot )
    -	    syslog(
    -		LOG_WARNING,
    -		"started as root without requesting chroot(), warning only" );
    -	}
    -
         /* Initialize our connections table. */
         connects = NEW( connecttab, max_connects );
         if ( connects == (connecttab*) 0 )

After patching this and re-building thttpd in the Ubuntu container, we
have a functioning statically linked binary:

    $ ./thttpd -D -l /dev/stderr -p 8080
    127.0.0.1 - - [04/Jan/2015:16:44:26 -0500] "GET / HTTP/1.1" 200 1351 "" "curl/7.37.0"

That line of output represents me running `curl` in another window.

## Automating the process

I have put together an environment to perform the above steps and
build a minimal Docker image with the resulting binary.  You can find
the code at <https://github.com/larsks/docker-image-thttpd>.

If you check out the code:

    $ git clone https://github.com/larsks/docker-image-thttpd
    $ cd docker-image-thttpd

And run `make`, this will:

1. build an Ubuntu-based image with scripts in place to produce a
   statically-linked thttpd,
1. Boot a container from that image and drop the static `thttpd`
   binary into a local directory, and
1. Produce a minimal Docker image containing just `thttpd` and a
   simple `index.html`.

The final image is just over 1MB in size, and downloads to a new
Kubernetes environment in seconds.  You can grab the finished image
via:

    docker pull larsks/thttpd

(Or you can grab the above repository from GitHub and build it
yourself locally).