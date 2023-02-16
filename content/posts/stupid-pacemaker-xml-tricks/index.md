---
categories: [tech]
aliases: ["/2015/02/19/stupid-pacemaker-xml-tricks/"]
title: Stupid Pacemaker XML tricks
date: "2015-02-19"
tags:
  - pacemaker
  - xml
  - xpath
---

I've recently spent some time working with [Pacemaker][], and ended up
with an interesting collection of [XPath][] snippets that I am publishing
here for your use and/or amusement.

[pacemaker]: http://clusterlabs.org/
[xpath]: http://www.w3.org/TR/xpath/

## Check if there are any inactive resources

    pcs status xml |
      xmllint --xpath '//resource[@active="false"]' - >&/dev/null &&
      echo "There are inactive resources"

This selects *any* resource (`//resource`) in the output of `pcs
status xml` that has the attribute `active` set to `false`.  If there
are no matches to this query, `xmllint` exits with an error code.

## Get a list of inactive resources

    pcs status xml |
      xmllint --xpath '//resource[@active="false"]/@id' - |
      tr ' ' '\n' |
      cut -f2 -d'"'

This uses the same xpath query as the previous snippet, but here we
then extract the `id` attribute of the matches and then print out all
the resulting ids, one per line.

## Check if there are *no* inactive resources

    ! pcs status xml |
      xmllint --xpath '//resource[@active="false"]' - &&
      echo "There are no inactive resources"

This is the opposite of our earlier snippet, and demonstrates the use
of `!` in a shell script to negate the success/failure of a shell
pipeline.

## Check top-level resources

    tmpfile=$(mktemp xmlXXXXXX)
    trap "rm -f $tmpfile" EXIT

    pcs status xml > $tmpfile
    xmllint --xpath '/crm_mon/resources/*/@id' $tmpfile |
    tr ' ' '\n'| cut -f2 -d'"' |
    while read id; do
      [ "$id" ] || continue
      if ! xmllint --xpath "
          /crm_mon/resources/*[@id='$id' and @active='true']|
          /crm_mon/resources/*[@id='$id']/*[@active='true']" \
          $tmpfile > /dev/null 2>&1; then
        echo "$id: no active resources" >&2
        exit 1
      fi
    done

This snippet checks that each top-level resource or resource container
(clone, resource group, etc.) has at least one active resources.
First we extract the `id` attribute from the just the top-level
contents of `/cr_mon/resources`:

    /crm_mon/resources/*/@id

And then we iterate over the extracted ids, and for each one, we check
if either (a) a resource with that id is active, or (b) if any child
of a resource with that id is active:

    /crm_mon/resources/*[@id='$id' and @active='true']|
    /crm_mon/resources/*[@id='$id']/*[@active='true']

# Wait for all resources to become inactive

    pcs set property stop-all-resources=true
    while pcs status xml |
        xmllint --xpath '//resource[@active="true"]' -; do
      sleep 1
    done

This is a good way to programatically wait for Pacemaker to finish
responding to setting `stop-all-resources=true`.

# Get a list of all top-level resources

    cibadmin -Q |
      xmllint --xpath '/cib/configuration/resources/*/@id' - |
      tr ' ' '\n' |
      cut -f2 -d'"'

This generates a list of the ids of "top-level" resources (either
standalone resources, or resource containers such as groups or
clones).

# Wait for all members of a resource container to become active

    id='neutron-scale-clone'
    while pcs status xml |
        xmllint --xpath "//clone[@id='$id']/resource[@active='false']" -; do
      sleep 1
    done

This waits until all children of the specified resource id become
active.

