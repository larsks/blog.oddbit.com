---
categories: [tech]
aliases: ["/2011/05/09/signing-data-with-ssh-agent/"]
title: Signing data with ssh-agent
date: "2011-05-09"
tags:
  - ssl
  - ssh
  - openssl
  - ssh-agent
  - openssh
  - rsa
  - cryptography
---

This is follow-up to my previous post, [Converting OpenSSH public keys][1].

OpenSSH allows one to use an _agent_ that acts as a proxy to your private key. When using an agent -- particularly with agent forwarding enabled -- this allows you to authenticate to a remote host without having to (a) repeatedly type in your password or (b) expose an unencrypted private key to remote systems.

If one is temtped to use SSH keys as authentication credentials outside of ssh, one would ideally be able to take advantage of the ssh agent for these same reasons.

This article discusses what is required to programmatically interact with the agent and with the OpenSSL libraries for signing data and verifying signatures.

#### Signing data with ssh-agent

The SSH agent does not provide clients with direct access to an unencrypted private key. Rather, it will accept data from the client and return the signature of the SHA1 hash of the data.

The agent communicates over a unix socket using the [ssh agent protocol][2] defined in [authfd.h][3]. The Python [Paramiko][4] libary (a pure-python implementation of ssh) includes support for interacting with an ssh agent.

Signing data is very simple:
    
    
    import hashlib
    import paramiko.agent
    
    data = 'something to sign'
    data_sha1 = hashlib.sha1(data).digest()
    a = paramiko.agent.Agent()
    key = a.keys[0]
    d = key.sign_ssh_data(None, data_sha1)
    

Internally, the agent computes the SHA1 digest for the data, signs this using the selected key, and returns a _signature_blob_ that varies depending on the key type in use. For an RSA signature, the result format is a series of (length, data) pairs, where the length is encoded as a four-byte unsigned integer. The response contains the following elements:

  1. algorithm name (ssh-rsa)
  2. rsa signature

For example, after signing some data using a 1024-bit private key, the value returned from sign_ssh_data looked like this:
    
    
    0000000: 0000 0007 7373 682d 7273 6100 0000 8027  ....ssh-rsa....'
    0000010: 953c 771c 5ee4 f4b0 9849 c061 0ac2 2adb  .<w.^....I.a..*.
    0000020: b53d 2bcb a545 8dbb d582 05e5 a916 6490  .=+..E........d.
    0000030: 1b67 3210 9bfc c74d d0ad 5011 394b a3fe  .g2....M..P.9K..
    0000040: 96e2 910b bbfd 19cd 73e5 6720 503a 95e1  ........s.g P:..
    0000050: 5b8b 63c4 14a3 ec3d bf57 846e f0b4 e66c  [.c....=.W.n...l
    0000060: ce5d 6327 6055 b4e2 3c14 c13f 8303 4b1a  .]c'`U..<..?..K.
    0000070: 7ce3 9f33 9e7c 7ca4 a97b 506d fa0b a39e  |..3.||..{Pm....
    0000080: cb53 befc d725 9cd1 a8af 6042 5ac8 01    .S...%....`BZ..
    

The first four bytes (0000 0007) are the length of the algorithm name (ssh-rsa). The next field is the length of the signature (0000 0080, or 128 bytes), followed by the signature data. This means we can extract the signature data like this:
    
    
    parts = []
    while d:
        len = struct.unpack('>I', d[:4])[0]
        bits = d[4:len+4]
        parts.append(bits)
        d = d[len+4:]
    
    sig = parts[1]
    open('signature', 'w').write(sig)
    

#### Signing the data with OpenSSL

##### Using M2Crypto

You can accomplish the same thing using the [M2Crypto][5] library for Python like this:
    
    
    import hashlib
    import M2Crypto.RSA
    
    data = 'something to sign'
    data_sha1 = hashlib.sha1(data).digest()
    key = M2Crypto.RSA.load_key('testkey')
    sig = key.sign(data_sha1)
    open('signature', 'w').write(sig)
    

This assumes that testkey is the private key file corresponding to the first key loaded into your agent in the previous example.

##### Using the command line

You can also generate an equivalent signature using the OpenSSL command line tools:
    
    
    echo -n 'something to sign' |
      openssl sha1  -binary |
      openssl pkeyutl -sign -inkey testkey -pkeyopt digest:sha1 > signature
    

Note that including -pkeyopt digest:sha1 is necessary to get a signature block that is compatible with the one returned by the ssh agent. The pkeyutl man page has this to say:

> In PKCS#1 padding if the message digest is not set then the supplied data is signed or verified directly instead of using a DigestInfo structure. If a digest is set then the a DigestInfo structure is used and its the length must correspond to the digest type.

#### Veryfying the data

You can verify the signature using the corresponding public key.

##### Using M2Crypto

This uses the [M2Crypto][5] module to verify the signature computed in the previous step:
    
    
    import hashlib
    import M2Crypto.RSA
    
    # let's pretend that you've read my previous blog post and have
    # created an "sshkey" module for reading the ssh public key format.
    import sshkey
    
    data = 'something to sign'
    data_sha1 = hashlib.sha1(data).digest()
    
    # read the signature generated in the previous step
    sig = open('signature').read()
    
    e,n = sshkey.load_rsa_pub_key('testkey.pub')
    key = M2Crypto.RSA.new_pub_key((
        M2Crypto.m2.bn_to_mpi(M2Crypto.m2.hex_to_bn(hex(e)[2:])),
        M2Crypto.m2.bn_to_mpi(M2Crypto.m2.hex_to_bn(hex(n)[2:])),
        ))
    
    if key.verify(data_sha1, sig):
      print 'Verified!'
    else:
      print 'Failed!'
    

If you have converted the ssh public key into a standard format, you could do this instead:
    
    
    import hashlib
    import M2Crypto.RSA
    
    data = 'something to sign'
    data_sha1 = hashlib.sha1(data).digest()
    
    # read the signature generated in the previous step
    sig = open('signature').read()
    
    key = M2Crypto.RSA.load_pub_key('testkey.pubssl')
    
    if key.verify(data_sha1, sig):
      print 'Verified!'
    else:
      print 'Failed!'
    

##### Using OpenSSL

We can do the same thing on the command line, but we'll first need to convert the ssh public key into a format useful to OpenSSL. This is easy if you have the private key handy...which we do:
    
    
    openssl rsa -in testkey -pubout > testkey.pubssl
    

And now we can verify the signature:
    
    
    echo 'something to sign' |
      openssl sha1  -binary |
      openssl pkeyutl -verify -sigfile signature \
        -pubin -inkey testkey.pubssl -pkeyopt digest:sha1
    

[1]: http://blog.oddbit.com/2011/05/08/converting-openssh-public-keys/
[2]: http://www.openbsd.org/cgi-bin/cvsweb/src/usr.bin/ssh/PROTOCOL.agent?rev=HEAD;content-type=text%2Fplain
[3]: http://www.openbsd.org/cgi-bin/cvsweb/src/usr.bin/ssh/authfd.h?rev=HEAD;content-type=text%2Fplain
[4]: http://www.lag.net/paramiko/
[5]: http://sandbox.rulemaker.net/ngps/m2/

