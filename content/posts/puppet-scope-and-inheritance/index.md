---
categories: [tech]
aliases: ["/2011/08/16/puppet-scope-and-inheritance/"]
title: Puppet, scope, and inheritance
date: "2011-08-16"
tags:
  - puppet
---

I note this here because it wasn't apparent to me from the Puppet documentation.

If you have a Puppet class like this:
    
    
    class foo {
      File {  ensure  => file,
              mode    => 600,
              }
    }
    

And you use it like this:
    
    
    class bar {
      include foo
    
      file { '/tmp/myfile': }
    }
    

Then /tmp/myfile will not be created. But if instead you do this:
    
    
    class bar inherits foo {
      file { '/tmp/myfile': }
    }
    

It will be created with mode 0600. In other words, if you use inherits then definitions in the parent class are available in the scope of your subclass. If you include, then definitions in he included class are "below" the scope of the including class.
