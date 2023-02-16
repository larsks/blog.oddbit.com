---
categories: [tech]
title: "Using KeyOxide"
date: "2022-11-13"
tags:
  - mastodon
  - gpg
  - pgp
  - keyoxide
---

In today's post, we look at [KeyOxide][], a service that allows you to cryptographically assert ownership of online resources using your GPG key. Some aspects of the service are less than obvious; in response to some questions I saw on Mastodon I though I would put together a short guide to making use of the service.

[keyoxide]: https://keyoxide.org/

We're going to look at the following high-level tasks:

1. [Create a GPG key](#step-1-create-a-gpg-keypair)

2. [Publish the GPG key](#step-2-publish-your-key)

3. [Use the GPG key to assert claims on online resources](#step-3-add-a-claim)

## Step 1: Create a GPG keypair

If you already have a keypair, skip on to "[Step 2: Publish your key](#step-2-publish-your-key)".

The first thing you need to do is set up a GPG[^1] keypair and publish it to a keyserver (or a [WKD endpoint][wkd]). There are many guides out there that step you through the process (for example, GitHub's guide on [Generating a new GPG key][]), but if you're in a hurry and not particularly picky, read on.

This assumes that you're using a recent version of GPG; at the time of this writing, the current GPG release is 2.3.8, but these instructions seem to work at least with version 2.2.27.

1. Generate a new keypair using the `--quick-gen-key` option:

    ```
    gpg --batch --quick-gen-key <your email address>
    ```
    This will use the GPG defaults for the key algorithm (varies by version) and expiration time (the key never expires[^2]).

2. When prompted, enter a secure passphrase.

3. GPG will create a keypair for you; you can view it after the fact by running:

    ```
    gpg -qk <your email address>
    ```

    You should see something like:

    ```
    pub   ed25519 2022-11-13 [SC] [expires: 2024-11-12]
          EC03DFAC71DB3205EC19BAB1404E03D044EE706B
    uid           [ultimate] testuser@example.com
    sub   cv25519 2022-11-13 [E]
    ```

    In the above output, `F79CE5D41D93C2C0E97F9A63C4178440F81E4261` is the *key fingerprint*. We're going to need this later.

Now you have created a GPG keypair!

[wkd]: https://wiki.gnupg.org/WKD
[generating a new gpg key]: https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key

[^1]: The pedantic among you will already be writing to me about how PGP is the standard and GPG is an implementation of that standard, but I'm going to stick with this nomenclature for the sake of simplicity.

[^2]: For some thoughts on key expiration, see [this question][] on the Information Security StackExchange.

[this question]: https://security.stackexchange.com/questions/14718/does-openpgp-key-expiration-add-to-security

## Step 2: Publish your key

If you've already published your key at <https://keys.openpgp.org/> or at a [WKD][] endpoint, skip on to "[Step 3: Add a claim](#step-3-add-a-claim)".

In order for KeyOxide to find your GPG key, it needs to be published at a known location. There are two choices:

- Publishing your key at the public keyserver at <https://keys.openpgp.org/>.
- Publishing your key using a [WKD][] service

In this post, we're only going to consider the first option.

1. Export your public key to a file using gpg's `--export` option:

    ```
    gpg --export -a <your email address> > mykey.asc
    ```

    This will create a file `mykey.asc` in your current directory that looks like:

    ```
    -----BEGIN PGP PUBLIC KEY BLOCK-----

    [...a bunch of base64 encoded text...]
    -----END PGP PUBLIC KEY BLOCK-----
    ```
2. Go to <https://keys.openpgp.org/upload>.

3. Select the key export you just created, and select "upload".

4. When prompted on the next page, select "Send Verification Email". Your key won't discoverable until you have received and responded to the verification email.

5. When you receive the email, select the verification link.

Now your key has been published! You can verify this by going to <https://keys.openpgp.org/> and searching for your email address.

## Step 3: Add a claim

You assert ownership of an online resource through a three step process:

1. Mark the online resource with your GPG key fingerprint. How you do this depends on the type of resource you're claiming; e.g., for GitHub you create a gist with specific content, while for claiming a DNS domain you create a `TXT` record.

2. Add a notation to your GPG key with a reference to the claim created in the previous step.

3. Update your published key.

In this post we're going to look at two specific examples; for other services, see the "Service providers" section of the [KeyOxide documentation][].

[keyoxide documentation]: https://docs.keyoxide.org/

In order to follow any of the following instructions, you're going to need to know your *key fingerprint*. When you show your public key by running `gpg -k`, you key fingerprint is the long hexadecimal string on the line following the line that starts with `pub `:

```
$ gpg -qk testuser@example.com
pub   ed25519 2022-11-13 [SC] [expires: 2024-11-12]
      EC03DFAC71DB3205EC19BAB1404E03D044EE706B      <--- THIS LINE HERE
uid           [ultimate] testuser@example.com
sub   cv25519 2022-11-13 [E]
```

### Add a claim to your GPG key

This is a set of common instructions that we'll use every time we need to add a claim to our GPG key.

1. Edit your GPG key using the `--edit-key` option:

    ```
    gpg --edit-key <your email address>
    ```

    This will drop you into the GPG interactive key editor.

2. Select a user id on which to operate using the `uid` command. If you created your key following the instructions earlier in this post, then you only have a single user id:

    ```
    gpg> uid 1
    ```

3. Add an annotation to the key using the `notation` command:

    ```
    gpg> notation
    ```

4. When prompted, enter the notation (the format of the notation depends on the service you're claiming; see below for details). For example, if we're asserting a Mastodon identity at hachyderm.io, we would enter:

    ```
    Enter the notation: proof@ariadne.id=https://hachyderm.io/@testuser
    ```

5. Save your changes with the `save` command:

    ```
    gpg> save
    ```

### Update your published key

After adding an annotation to your key locally, you need to publish those changes. One way of doing this is simply following the [instructions for initially uploading your public key](#step-2-publish-your-key):

1. Export the key to a file:

    ```
    gpg --export -a <your email address> > mykey.asc
    ```

2. Upload your key to <https://keys.openpgp.org/upload>.

You won't have to re-verify your key.

Alternately, you can configure gpg so that you can publish your key from the command line. Create or edit `$HOME/.gnupg/gpg.conf` and add the following line:

```
keyserver hkps://keys.openpgp.org
```

Now every time you need to update the published version of your key:

1. Upload your public key using the `--send-keys` option along with your key fingerprint, e.g:

    ```
    gpg --send-keys EC03DFAC71DB3205EC19BAB1404E03D044EE706B
    ```

### Claiming a Mastodon identity

1. On your favorite Mastodon server, go to your profile and select "Edit profile".

2. Look for the "Profile metadata section"; this allows you to associate four bits of metadata with your Mastodon profile. Assuming that you still have a slot free, give it a name (it could be anything, I went with "Keyoxide claim"), and for the value enter:

    ```
    openpgp4fpr:<your key fingerprint>
    ```

    E.g., given the `gpg -k` output shown above, I would enter:

    ```
    openpgp4fpr:EC03DFAC71DB3205EC19BAB1404E03D044EE706B
    ```

3. Click "Save Changes"

Now, [add the claim to your GPG key](#add-a-claim-to-your-gpg-key) by adding the notation `proof@ariadne.id=https://<your mastodon server>/@<your mastodon username`. I am @larsks@hachyderm.io, so I would enter:

```
proof@ariadne.id=https://hachyderm.io/@larsks
```

After adding the claim, [update your published key](#update-your-published-key).

### Claiming a Github identity

1. Create a [new gist][] (it can be either secret or public).

2. In your gist, name the filename `openpgp.md`.

3. Set the content of that file to:

    ```
    openpgp4fpr:<your key fingerprint>
    ```

[new gist]: https://gist.github.com

Now, [add the claim to your GPG key](#add-a-claim-to-your-gpg-key) by adding the notation `proof@ariadne.id=https://gist.github.com/larsks/<gist id>`. You can see my claim at <https://gist.github.com/larsks/9224f58cf82bdf95ef591a6703eb91c7>; the notation I added to my key is:

```
proof@ariadne.id=https://gist.github.com/larsks/9224f58cf82bdf95ef591a6703eb91c7
```

After adding the claim, [update your published key](#update-your-published-key).

## Step 4: View your claims

You'll note that none of the previous steps required interacting with [KeyOxide][]. That's because KeyOxide doesn't actually store any of your data: it just provides a mechanism for visualizing and verifying claims.

You can look up an identity by email address or by GPG key fingerprint.

To look up an identity using an email address:

1. Go to `https://keyoxide.org/<email address`. For example, to find my identity, visit <https://keyoxide.org/lars@oddbit.com>.

To look up an identity by key fingerprint:

1. Go to `https://keyoxide.org/<fingerprint>`. For example, to find my identity, visit <https://keyoxide.org/3e70a502bb5255b6bb8e86be362d63a80853d4cf>.
