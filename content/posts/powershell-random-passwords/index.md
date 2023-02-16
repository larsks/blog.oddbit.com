---
categories: [tech]
aliases: ["/2012/11/04/powershell-random-passwords/"]
title: Generating random passwords in PowerShell
date: "2012-11-04"
tags:
  - powershell
  - windows
  - passwords
---

I was looking for PowerShell solutions for generating a random password (in
order to set the Administrator password on a Windows instance provisioned in
[OpenStack][]), and found several solutions using the GeneratePassword method
of `System.Web.Security.Membership` (documentation [here][generatepassword]),
along the lines of [this][gist-4011878]:

[openstack]: http://www.openstack.org/
[generatepassword]: http://msdn.microsoft.com/en-us/library/system.web.security.membership.generatepassword.aspx
[gist-4011878]: https://gist.github.com/4011878

    Function New-RandomComplexPassword ($length=8)
    {
        $Assembly = Add-Type -AssemblyName System.Web
        $password = [System.Web.Security.Membership]::GeneratePassword($length,2)
        return $password
    }

While this works, I was unhappy with the generated passwords: they
were difficult to type or transcribe because they make heavy use of
punctuation.  For example:

- `(O;RK_wx(IcD;<V`
- `+3N)lkU5r)nHiL#`

These looks more like line noise (remember that?  No?  Get off my
lawn...) than anything else and feel very unnatural to type.

I was looking for longer strings consisting primarily of letters and
digits.  Thanks to Hey, Scripting Guy I learned about the Get-Random
and ForEach-Object methods (and the % alias for the latter), and ended
up with [the following][gist-4011916]:

[gist-4011916]: https://gist.github.com/4011916

    # Generate a random password
    # Usage: random-password <length>
    Function random-password ($length = 15)
    {
        $punc = 46..46
        $digits = 48..57
        $letters = 65..90 + 97..122
         
        # Thanks to
        # https://blogs.technet.com/b/heyscriptingguy/archive/2012/01/07/use-pow
        $password = get-random -count $length `
            -input ($punc + $digits + $letters) |
                % -begin { $aa = $null } `
                -process {$aa += [char]$_} `
                -end {$aa}
         
        return $password
    }

This generates strings of letters and digits (and ".") that look something like:

- `2JQ0bW7VMqcm4UB`
- `V4DObnQl0vJX1wC`

I'm a lot happier with this.

