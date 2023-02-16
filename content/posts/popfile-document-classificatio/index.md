---
aliases:
- /2012/11/08/popfile-document-classification/
- /post/2012-11-08-popfile-document-classification
categories:
- tech
date: '2012-11-08'
tags:
- bayes
- analytics
title: Document classification with POPFile
---

I recently embarked upon a quest to categorize a year's worth of
trouble tickets (around 15000 documents total).  We wanted to see what
sort of things are generating the most work for our helpdesk staff so
that we can identify areas in which improvements would have the
biggest impact.  One of my colleagues took a first pass at the data by
manually categorizing the tickets based on their subject.  This
resulted in some useful data, but in the end just over 40% of the
tickets are still uncategorized.

I was convinced that we could do better than that by taking into
account the actual content of the trouble tickets.  This seemed like a
good task for a [Bayesian filter][] -- a tool that uses the
statistical probability of words to categorize documents, and is most
commonly used to differentiate "spam" from "non-spam" messages in
email.  Because of this common use case, many of the tools out there
are built explicitly to make binary (spam/not-spam) determinations,
while for my purposes I needed something that was capable for sorting
documents into multiple categories.

I finally stumbled across [POPFile][], a tool that does almost exactly
what I want.  Out of the box, POPFile is designed to act as a proxy
between you and a POP mailbox, categorizing messages as your mail
client retrieves them from a server.  While this is tremendously
convenient for use categorizing email, it would be a sub-optimal
interface for categorizing a collection of existing documents.

Fortunately, POPFile offers an [XML-RPC API][] that allows programmatic
interaction with the classification engine.  Usage is relatively
simple; first you acquire a connection to the XML-RPC API and
establish a session key:

    popfile = ServerProxy("http://localhost:8081")
    api = popfile.POPFile.API
    session = api.get_session_key('admin', '')

And then for each document, perform whatever transformations you wish
to make (I'm building a minimal mail header) and then pass it to the
`handle_message()` method:

    with tempfile.NamedTemporaryFile() as fd:
        fd.write('Subject: %s [%s]\n' % (subject, id))
        fd.write('Message-ID: <%s@localhost>\n' % id)
        fd.write('\n')
        fd.write('\n'.join(text))
        fd.flush()

        # Pass file to POPFile service.
        bucket = api.handle_message(session, fd.name, '/dev/null')

The `handle_message()` call takes three parameters:

- The session key,
- A path to the input file,
- A path to the output file (POPFile returns the message with header
  modifications)

In this example, I'm passing `/dev/null` as the third parameter
because I don't care about the data returned from POPFile.

Initially, POPFile will not perform any categorization of documents.
After manually categorizing just a few documents, two things happen:

- POPFile will start using any [magnets][] you have defined, which are
  keyword rules that automatically assign documents to a given
  category.
- For documents that do not match any magnet rules, POPFile will
  attempt to categorize them using the Bayesian inference engine.

POPFile provides a web interface for interacting with the
classification engine.  In particular, this is where you go to
manually classify documents, which further enhances the accuracy of
the Bayesian filters.  I got bored after manually categorizing on the
order of 300 or 400 tickets and just fed the rest of the collection
into the filter.  I suspect the accuracy of the system is somewhere
between 70% and 80% (based on POPFiles's estimates of accuracy while I
was manually categorizing documents).

For more information:

- [POPFile] website

[bayesian filter]: https://en.wikipedia.org/wiki/Bayesian_spam_filtering
[popfile]: http://getpopfile.org/
[xml-rpc api]: http://getpopfile.org/docs/popfilemodules:xmlrpc#popfile_xml-rpc_api
[magnets]: http://getpopfile.org/docs/glossary:amagnet