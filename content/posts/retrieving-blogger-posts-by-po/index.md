---
aliases:
- /2010/01/29/retrieving-blogger-posts-by-post-id/
- /post/2010-01-29-retrieving-blogger-posts-by-post-id
categories:
- tech
date: '2010-01-29'
tags:
- python
- blogger
- api
- gdata
title: Retrieving Blogger posts by post id
---

I spent some time recently trying to figure out, using Google's [gdata][1] API, how to retrieve a post from a [Blogger][2] blog if I know corresponding post id. As far as I can tell there is no obvious way of doing this, at least not using the gdata.blogger.client api, but after much nashing of teeth I came up with the following solution.

Given client, a [gdata.blogger.client][3] instance, and blog, a [gdata.blogger.data.Blog][4] instance, the following code will return a [gdata.blogger.data.BlogPost][4] instance:
    
    
    post = client.get_feed(blog.get_post_link().href
              + '/%s' % post_id,
            auth_token=client.auth_token,
            desired_class=gdata.blogger.data.BlogPost)
    

I'm not sure if this is the canonical solution or not, but it appears to work for me.

[1]: http://code.google.com/apis/gdata/docs/2.0/basics.html
[2]: http://www.blogger.com/
[3]: http://gdata-python-client.googlecode.com/svn/trunk/pydocs/gdata.blogger.client.html
[4]: http://gdata-python-client.googlecode.com/svn/trunk/pydocs/gdata.blogger.data.html