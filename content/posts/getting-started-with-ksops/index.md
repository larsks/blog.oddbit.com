---
categories:
- tech
date: '2021-03-09'
draft: false
tags:
- openshift
- kubernetes
- ksops
- gpg
title: Getting started with KSOPS

---

[Kustomize][] is a tool for assembling Kubernetes manifests from a
collection of files. We're making extensive use of Kustomize in the
[operate-first][] project. In order to keep secrets stored in our
configuration repositories, we're using the [KSOPS][] plugin, which
enables Kustomize to use [sops][] to encrypt/files using GPG.

[kustomize]: https://kustomize.io/
[ksops]: https://github.com/viaduct-ai/kustomize-sops
[sops]: https://github.com/mozilla/sops
[operate-first]: https://www.operate-first.cloud/

In this post, I'd like to walk through the steps necessary to get
everything up and running.

## Set up GPG

We encrypt files using GPG, so the first step is making sure that you
have a GPG keypair and that your public key is published where other
people can find it.

### Install GPG

GPG will be pre-installed on most Linux distributions. You can check
if it's installed by running e.g. `gpg --version`. If it's not
installed, you will need to figure out how to install it for your
operating system.

### Create a key

Run the following command to create a new GPG keypair:

```
gpg --full-generate-key
```

This will step you through a series of prompts. First, select a key
type. You can just press `<RETURN>` for the default:

```
gpg (GnuPG) 2.2.25; Copyright (C) 2020 Free Software Foundation, Inc.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Please select what kind of key you want:
   (1) RSA and RSA (default)
   (2) DSA and Elgamal
   (3) DSA (sign only)
   (4) RSA (sign only)
  (14) Existing key from card
Your selection?
```

Next, select a key size. The default is fine:

```
RSA keys may be between 1024 and 4096 bits long.
What keysize do you want? (3072)
Requested keysize is 3072 bits
```

You will next need to select an expiration date for your key.  The
default is "key does not expire", which is a fine choice for our
purposes. If you're interested in understanding this value in more
detail, the following articles are worth reading:

- [Does OpenPGP key expiration add to security?][expire-1]
- [How to change the expiration date of a GPG key][expire-2]

[expire-1]: https://security.stackexchange.com/questions/14718/does-openpgp-key-expiration-add-to-security/79386#79386
[expire-2]: https://www.g-loaded.eu/2010/11/01/change-expiration-date-gpg-key/

Setting an expiration date will require that you periodically update
the expiration date (or generate a new key).

```
Please specify how long the key should be valid.
         0 = key does not expire
      <n>  = key expires in n days
      <n>w = key expires in n weeks
      <n>m = key expires in n months
      <n>y = key expires in n years
Key is valid for? (0)
Key does not expire at all
Is this correct? (y/N) y
```

Now you will need to enter your identity, which consists of your name,
your email address, and a comment (which is generally left blank).
Note that you'll need to enter `o` for `okay` to continue from this
prompt.

```
GnuPG needs to construct a user ID to identify your key.

Real name: Your Name
Email address: you@example.com
Comment:
You selected this USER-ID:
    "Your Name <you@example.com>"

Change (N)ame, (C)omment, (E)mail or (O)kay/(Q)uit? o
```

Lastly, you need to enter a password. In most environments, GPG will
open a new window asking you for a passphrase. After you've entered and
confirmed the passphrase, you should see your key information on the
console:

```
gpg: key 02E34E3304C8ADEB marked as ultimately trusted
gpg: revocation certificate stored as '/home/lars/tmp/gpgtmp/openpgp-revocs.d/9A4EB5B1F34B3041572937C002E34E3304C8ADEB.rev'
public and secret key created and signed.

pub   rsa3072 2021-03-11 [SC]
      9A4EB5B1F34B3041572937C002E34E3304C8ADEB
uid                      Your Name <you@example.com>
sub   rsa3072 2021-03-11 [E]
```

### Publish your key

You need to publish your GPG key so that others can find it. You'll
need your key id, which you can get by running `gpg -k --fingerprint`
like this (using your email address rather than mine):

```
$ gpg -k --fingerprint lars@oddbit.com
```

The output will look like the following:

```
pub   rsa2048/0x362D63A80853D4CF 2013-06-21 [SC]
      Key fingerprint = 3E70 A502 BB52 55B6 BB8E  86BE 362D 63A8 0853 D4CF
uid                   [ultimate] Lars Kellogg-Stedman <lars@oddbit.com>
uid                   [ultimate] keybase.io/larsks <larsks@keybase.io>
sub   rsa2048/0x042DF6CF74E4B84C 2013-06-21 [S] [expires: 2023-07-01]
sub   rsa2048/0x426D9382DFD6A7A9 2013-06-21 [E]
sub   rsa2048/0xEE1A8B9F9369CC85 2013-06-21 [A]
```

Look for the `Key fingerprint` line, you want the value after the `=`.
Use this to publish your key to `keys.openpgp.org`:


```
gpg --keyserver keys.opengpg.org \
  --send-keys '3E70 A502 BB52 55B6 BB8E  86BE 362D 63A8 0853 D4CF'
```

You will shortly receive an email to the address in your key asking
you to approve it. Once you have approved the key, it will be
published on <https://keys.openpgp.org> and people will be able to look
it up by address or key id.  For example, you can find my public key
at <https://keys.openpgp.org/vks/v1/by-fingerprint/3E70A502BB5255B6BB8E86BE362D63A80853D4CF>.

## Installing the Tools

In this section, we'll get all the necessary tools installed on your
system in order to interact with a repository using Kustomize and
KSOPS.

### Install Kustomize

Pre-compiled binaries of Kustomize are published [on
GitHub][gh-kustomize]. To install the command, navigate to the current
release ([v4.0.5][] as of this writing)  and download the appropriate
tarball for your system. E.g, for an x86-64 Linux environment, you
would grab [kustomize_v4.0.5_linux_amd64.tar.gz][].

[gh-kustomize]: https://github.com/kubernetes-sigs/kustomize/releases
[v4.0.5]: https://github.com/kubernetes-sigs/kustomize/releases/tag/kustomize%2Fv4.0.5
[kustomize_v4.0.5_linux_amd64.tar.gz]: https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2Fv4.0.5/kustomize_v4.0.5_linux_amd64.tar.gz

The tarball contains a single file. You need to extract this file and
place it somwhere in your `$PATH`.  For example, if you use your
`$HOME/bin` directory, you could run:

```
tar -C ~/bin -xf kustomize_v4.0.5_linux_amd64.tar.gz
```

Or to install into `/usr/local/bin`:

```
sudo tar -C /usr/local/bin -xf kustomize_v4.0.5_linux_amd64.tar.gz
```

Run `kustomize` with no arguments to verify the command has been
installed correctly.

### Install sops

The KSOPS plugin relies on the [sops][] command, so we need to install
that first. Binary releases are published on GitHub, and the current
release is [v3.6.1][].

Instead of a tarball, the project publishes the raw binary as well as
packages for a couple of different Linux distributions. For
consistency with the rest of this post we're going to grab the [raw
binary][sops-v3.6.1.linux]. We can install that into `$HOME/bin` like this:

```
curl -o ~/bin/sops https://github.com/mozilla/sops/releases/download/v3.6.1/sops-v3.6.1.linux
chmod 755 ~/bin/sops
```

[v3.6.1]: https://github.com/mozilla/sops/releases/tag/v3.6.1
[sops-v3.6.1.linux]: https://github.com/mozilla/sops/releases/download/v3.6.1/sops-v3.6.1.linux

### Install KSOPS

KSOPS is a Kustomize plugin. The `kustomize` command looks for plugins
in subdirectories of `$HOME/.config/kustomize/plugin`. Directories are
named after an API and plugin name. In the case of KSOPS, `kustomize`
will be looking for a plugin named `ksops` in the
`$HOME/.config/kustomize/plugin/viaduct.ai/v1/ksops/` directory.

The current release of KSOPS is [v2.4.0][], which is published as a
tarball. We'll start by downloading
[ksops_2.4.0_Linux_x86_64.tar.gz][], which contains the following
files:

```
LICENSE
README.md
ksops
```

To extract the `ksops` command to `$HOME/bin`, you can run:

```
mkdir  -p ~/.config/kustomize/plugin/viaduct.ai/v1/ksops/
tar -C ~/.config/kustomize/plugin/viaduct.ai/v1/ksops -xf ksops_2.4.0_Linux_x86_64.tar.gz ksops
```

[v2.4.0]: https://github.com/viaduct-ai/kustomize-sops/releases/tag/v2.4.0
[ksops_2.4.0_Linux_x86_64.tar.gz]: https://github.com/viaduct-ai/kustomize-sops/releases/download/v2.4.0/ksops_2.4.0_Linux_x86_64.tar.gz


## Test it out

Let's create a simple Kustomize project to make sure everything is
installed and functioning.

Start by creating a new directory and changing into it:

```
mkdir kustomize-test
cd kustomize-test
```

Create a `kustomization.yaml` file that looks like this:

```
generators:
  - secret-generator.yaml
```

Put the following content in `secret-generator.yaml`:

```
---
apiVersion: viaduct.ai/v1
kind: ksops
metadata:
  name: secret-generator
files:
  - example-secret.enc.yaml
```

This instructs Kustomize to use the KSOPS plugin to generate content
from the file `example-secret.enc.yaml`.

Configure `sops` to use your GPG key by default by creating a
`.sops.yaml` (note the leading dot) similar to the following (you'll
need to put your GPG key fingerprint in the right place):

```
creation_rules:
  - encrypted_regex: "^(users|data|stringData)$"
    pgp: <YOUR KEY FINGERPRINT HERE>
```

The `encrypted_regex` line tells `sops` which attributes in your YAML
files should be encrypted. The `pgp` line is a (comma delimited) list
of keys to which data will be encrypted.

Now, edit the file `example-secret.enc.yaml` using the `sops` command.
Run:

```
sops example-secret.enc.yaml
```

This will open up an editor with some default content. Replace the
content with the following:


```
apiVersion: v1
kind: Secret
metadata:
    name: example-secret
type: Opaque
stringData:
    message: this is a test
```

Save the file and exit your editor. Now examine the file; you will see
that it contains a mix of encrypted and unencrypted content. When
encrypted with my private key, it looks like this:

```
$ cat example-secret.enc.yaml
{
	"data": "ENC[AES256_GCM,data:wZvEylsvhfU29nfFW1PbGqyk82x8+Vm/3p2Y89B8a1A26wa5iUTr1hEjDYrQIGQq4rvDyK4Bevxb/PrTzdOoTrYIhaerEWk13g9UrteLoaW0FpfGv9bqk0c12OwTrzS+5qCW2mIlfzQpMH5+7xxeruUXO7w=,iv:H4i1/Znp6WXrMmmP9YVkz+xKOX0XBH7kPFaa36DtTxs=,tag:bZhSzkM74wqayo7McV/VNQ==,type:str]",
	"sops": {
		"kms": null,
		"gcp_kms": null,
		"azure_kv": null,
		"hc_vault": null,
		"lastmodified": "2021-03-12T03:11:46Z",
		"mac": "ENC[AES256_GCM,data:2NrsF6iLA3zHeupD314Clg/WyBA8mwCn5SHHI5P9tsOt6472Tevdamv6ARD+xqfrSVWz+Wy4PtWPoeqZrFJwnL/qCR4sdjt/CRzLmcBistUeAnlqoWIwbtMxBqaFg9GxTd7f5q0iHr9QNWGSVV3JMeZZ1jeWyeQohAPpPufsuPQ=,iv:FJvZz8SV+xsy4MC1W9z1Vn0s4Dzw9Gya4v+rSpwZLrw=,tag:pfW8r5856c7qetCNgXMyeA==,type:str]",
		"pgp": [
			{
				"created_at": "2021-03-12T03:11:45Z",
				"enc": "-----BEGIN PGP MESSAGE-----\n\nwcBMA0Jtk4Lf1qepAQgAGKwk6zDMPUYbUscky07v/7r3fsws3pTVRMgpEdhTra6x\nDxiMaLnjTKJi9fsB7sQuh/PTGWhXGuHtHg0YBtxRkuZY0Kl6xKXTXGBIBhI/Ahgw\n4BSz/rE7gbz1h6X4EFml3e1NeUTvGntA3HjY0o42YN9uwsi9wvMbiR4OLQfwY1gG\np9/v57KJx5ipEKSgt+81KwzOhuW79ttXd2Tvi9rjuAfvmLBU9q/YKMT8miuNhjet\nktNwXNJNpglHJta431YUhPZ6q41LpgvQPMX4bIZm7i7NuR470njYLQPe7xiGqqeT\nBcuF7KkNXGcDu9/RnIyxK4W5Bo9NEa06TqUGTHLEENLgAeSzHdQdUwx/pLLD6OPa\nv/U34YJU4JngqOGqTuDu4orgwLDg++XysBwVsmFp1t/nHvTkwj57wAuxJ4/It/9l\narvRHlCx6uA05IXukmCTvYMPRV3kY/81B+biHcka7uFUOQA=\n=x+7S\n-----END PGP MESSAGE-----",
				"fp": "3E70A502BB5255B6BB8E86BE362D63A80853D4CF"
			}
		],
		"encrypted_regex": "^(users|data|stringData)$",
		"version": "3.6.1"
	}
}
```

Finally, attempt to render the project with Kustomize by running:

```
kustomize build --enable-alpha-plugins
```

This should produce on stdout the unencrypted content of your secret:

```
apiVersion: v1
kind: Secret
metadata:
    name: example-secret
type: Opaque
stringData:
    message: this is a test
```
