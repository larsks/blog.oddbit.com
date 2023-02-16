---
aliases:
- /2010/08/06/importing-vcard-contacts-into-lg-420g/
- /post/2010-08-06-importing-vcard-contacts-into-lg-420g
categories:
- tech
date: '2010-08-06'
tags:
- phone
- vcard
- sync
- contacts
- import
title: Importing vCard contacts into an LG 420G
---

Alix recently acquired an LG 420G from [TracFone][1]. She was interested in getting all of her contacts onto the phone, which at first seemed like a simple task -- transfer a vCard (.vcf) file to the phone via Bluetooth, and the phone would import all the contacts. This turned out to be a great idea in theory, but in practice there was a fatal flaw -- while the phone did indeed import the contacts, it only imported names and the occasional note or email address. There were no phone numbers.

Thus began the long investigation to find out exactly what the phone expected the contacts to look like.

# EOL format

The LG 420G needs DOS end-of-line (CRLF), otherwise it won't recognize more than a single contact in your file. There are a number of ways to convert EOL style in a text document; I used the unix2dos tool.

# Phone number labels

In our source vCard files, telephone numbers were typically listed with one qualifier, like this:
    
    
    TEL;WORK:555-555-5555
    TEL;HOME:555-555-5555
    TEL;CELL:555-555-5555
    

I created new contact entry on the phone and sent it back to my computer, and found that the telephone numbers were labelled with two qualifiers (and a character set identifier), like this:
    
    
    TEL;HOME;CELL;CHARSET=UTF-8:1111111111
    TEL;WORK;VOICE;CHARSET=UTF-8:2222222222
    TEL;HOME;VOICE;CHARSET=UTF-8:3333333333
    

So, the first thing we needed to do was to transform the phone number entries in our original list into the format expected by the 420G. I extracted a list of all the unique phone number labels, like this:
    
    
    grep TEL contacts.vcf | cut -f1 -d: | sort -u
    

Which resulted in this list:
    
    
    TEL;CELL
    TEL;HOME
    TEL;HOME;PREF
    TEL;PAGER
    TEL;PREF
    TEL;PREF;CELL
    TEL;PREF;FAX
    TEL;WORK
    TEL;WORK;PREF
    

I used this to generate the following sed script:
    
    
    s/TEL;HOME;PREF/TEL;HOME;VOICE/
    t
    s/TEL;HOME/TEL;HOME;VOICE/
    t
    s/TEL;CELL/TEL;HOME;CELL/
    t
    s/TEL;WORK;PREF/TEL;WORK;VOICE/
    t
    s/TEL;PREF;CELL/TEL;WORK;CELL/
    t
    s/TEL;PREF;FAX/TEL;WORK;FAX/
    t
    s/TEL;WORK/TEL;WORK;VOICE/
    t
    s/TEL;PREF/TEL;WORK;VOICE/
    t
    s/TEL;PAGER/TEL;WORK;PAGER/
    t
    

Running this over all the contacts gives us the following list of distinct labels:
    
    
    TEL;HOME;CELL
    TEL;HOME;VOICE
    TEL;WORK;CELL
    TEL;WORK;FAX
    TEL;WORK;PAGER
    TEL;WORK;VOICE
    

# No dashes in phone numbers (really, LG?)

It turns out that the 420G does not accept anything other than digits in phone numbers. So, after processing the labels with the above sed script we fix up the data with the following awk script:
    
    
    # Set input and output field separators to ":".
    BEGIN {
      FS=":"
      OFS=":"
    }
    
    # Remove anything not a digit from the phone number.
    /TEL;/ {
      gsub("[^0-9]", "", $2)
    }
    
    {
      print
    }
    

# And we're off!

With these transformations in place, the LG 420G was able to successfully import the contacts. I automated the whole process with the following Makefile:
    
    
    SED = gsed
    AWK = awk
    
    FILTERS = \
        fix-tel-labels.sed \
        remove-non-digits.awk
    
    all: all-contacts-filtered.vcf
    
    all-contacts-filtered.vcf: all-contacts-orig.vcf $(FILTERS)
      $(SED) -f fix-tel-labels.sed $< | \
        $(AWK) -f remove-non-digits.awk | \
        unix2dos > $@
    

[1]: http://www.tracfone.com/