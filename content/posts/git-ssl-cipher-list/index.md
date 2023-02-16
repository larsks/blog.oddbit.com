---
categories: [tech]
title: "Teach git about GIT_SSL_CIPHER_LIST"
date: "2015-05-08"
tags:
- git
- pull-request
---

Someone named [hithard][] on [StackOverflow][] was trying to clone a git repository via https, and was [running into an odd error][question]: "Cannot communicate securely with peer: no common encryption algorithm(s).". This was due to the fact that the server (`openhatch.org`) was configured to use a cipher suite that was not supported by default in the underlying SSL library (which could be either [OpenSSL][] or [NSS][], depending on how git was built).

[hithard]: https://stackoverflow.com/users/4713895/hithard
[question]: https://stackoverflow.com/a/30090725/147356
[stackoverflow]: https://stackoverflow.com/
[openssl]: https://www.openssl.org/
[nss]: https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSS

Many applications allow the user to configure an explicit list of ciphers to consider when negotiating a secure connection. For example, [curl][] has the [CURLOPT_SSL_CIPHER_LIST][] option. This turns out to be especially relevant because git relies on [libcurl][] for all of its http operations, which means all we need to do is (a) create a new configuration option for git, and then (b) pass that value through to libcurl.

[curl]: https://curl.haxx.se/
[libcurl]: https://curl.haxx.se/libcurl/
[curlopt_ssl_cipher_list]: https://curl.haxx.se/libcurl/c/CURLOPT_SSL_CIPHER_LIST.html
[sslciphersuite]: https://httpd.apache.org/docs/trunk/mod/mod_ssl.html#sslciphersuite

I took a look at the code and it turned out to be surprisingly easy. The functional part of the patch ends up being less than 10 lines total:

```
diff --git a/http.c b/http.c
index 679862006..c5e947965 100644
--- a/http.c
+++ b/http.c
@@ -35,6 +35,7 @@ char curl_errorstr[CURL_ERROR_SIZE];
 static int curl_ssl_verify = -1;
 static int curl_ssl_try;
 static const char *ssl_cert;
+static const char *ssl_cipherlist;
 #if LIBCURL_VERSION_NUM >= 0x070903
 static const char *ssl_key;
 #endif
@@ -153,6 +154,8 @@ static int http_options(const char *var, const char *value, void *cb)
                curl_ssl_verify = git_config_bool(var, value);
                return 0;
        }
+       if (!strcmp("http.sslcipherlist", var))
+               return git_config_string(&ssl_cipherlist, var, value);
        if (!strcmp("http.sslcert", var))
                return git_config_string(&ssl_cert, var, value);
 #if LIBCURL_VERSION_NUM >= 0x070903
@@ -327,6 +330,13 @@ static CURL *get_curl_handle(void)
        if (http_proactive_auth)
                init_curl_http_auth(result);

+       if (getenv("GIT_SSL_CIPHER_LIST"))
+               ssl_cipherlist = getenv("GIT_SSL_CIPHER_LIST");
+
+       if (ssl_cipherlist != NULL && *ssl_cipherlist)
+               curl_easy_setopt(result, CURLOPT_SSL_CIPHER_LIST,
+                               ssl_cipherlist);
+
        if (ssl_cert != NULL)
                curl_easy_setopt(result, CURLOPT_SSLCERT, ssl_cert);
        if (has_cert_password())
```

I [submitted this patch][] to the git mailing list, and after some discussion and a few revisions it was accepted.  This changed was [committed to git][] on May 8, 2015.


[submitted this patch]: https://marc.info/?l=git&m=143100824118409&w=2
[committed to git]: https://github.com/git/git/commit/f6f2a9e42d14e61429af418d8038aa67049b3821
