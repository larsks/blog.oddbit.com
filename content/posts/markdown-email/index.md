---
categories: [tech]
aliases: ["/2012/08/09/markdown-email/"]
title: Markdown in your Email
date: "2012-08-09"
---

I really like [Markdown][1], a minimal markup language designed to be readable as plain text that can be rendered into structurally valid HTML. Markdown is already used on sites such as [GitHub][2] and all the [StackExchange][3] sites.

I use Markdown often enough that it's become ingrained in my fingers, to the point that I've started unconsciously using Markdown syntax in my email. This isn't particularly useful by itself, although it means that I can take a message and render it to something pretty if I decide it needs to go somewhere other than my sent mail folder.

I thought it would be fun to implement something that would actually render Markdown syntax in my outbound email and render it into an HTML attachment. I spent a little time last night putting together a [small Python script][4] that does exactly that:

- It looks for a leading `<!-- markdown -->` in a message body.
- It renders the markdown to HTML.
- It transforms the message into a `multipart/mixed` message.
- It attaches the rendered content as `text/html`.
- It attaches the original message as `text/plain`.
- It attaches any signature that was found in the original message as `text/plain`

I have Mutt configured to pass outbound email through this filter by setting the `sendmail` variable...

    set sendmail="~/.mutt/bin/sendmail"  

...to point to a small shell script that passes everything off to [procmail][5]:

    #!/bin/sh
    exec procmail -m msmtp_args="$*" $HOME/.procmail/rc.sent

And then `procmail` filters outbound messages before sending them via `msmtp`:

    # Render markdown email to HTML
    :0f
    | $HOME/.mutt/bin/markdownmail
    
    # Send via msmtp
    :0w
    | msmtp $msmtp_args

It's not especially robust but it seems to work so far.

[1]: http://daringfireball.net/projects/markdown/
[2]: http://github.com/
[3]: http://stackexchange.com/sites
[4]: https://github.com/larsks/mutt-utils/blob/master/markdownmail.py
[5]: http://www.procmail.org/

