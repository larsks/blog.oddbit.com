---
categories: [tech]
aliases: ["/2019/04/25/writing-ansible-filter-plugins/"]
title: "Writing Ansible filter plugins"
date: "2019-04-25"
tags:
- "ansible"
- "python"
---

I often see questions from people who are attemping to perform complex text transformations in their [Ansible][] playbooks. While I am a huge fan of Ansible, data transformation is not one of its strong  points. For example, this past week someone [asked a question][55854394] on Stack Overflow in which they were attempting to convert the output of the [keytool][] command into a list of dictionaries.  The output of the `keytool -list -v` command looks something like this:

[ansible]: https://www.ansible.com/
[55854394]: https://stackoverflow.com/questions/55853384/ansible-build-list-dictionary-with-from-list-of-strings/55854394
[keytool]: https://docs.oracle.com/javase/8/docs/technotes/tools/unix/keytool.html


```
Keystore type: PKCS12
Keystore provider: SUN

Your keystore contains 2 entries

Alias name: alias2
Creation date: Apr 25, 2019
Entry type: PrivateKeyEntry
Certificate chain length: 1
Certificate[1]:
Owner: CN=Alice McHacker, OU=Unknown, O=Example Corp, L=Boston, ST=MA, C=US
Issuer: CN=Alice McHacker, OU=Unknown, O=Example Corp, L=Boston, ST=MA, C=US
Serial number: 5c017636
Valid from: Thu Apr 25 23:22:37 EDT 2019 until: Wed Jul 24 23:22:37 EDT 2019
Certificate fingerprints:
	 SHA1: FB:AC:36:08:F6:3C:C0:CF:E1:D7:E6:7D:2F:31:BF:BE:5A:C8:7A:C6
	 SHA256: 73:F1:EC:61:6B:63:93:F5:BE:78:23:A1:79:14:7D:F0:A3:9A:D8:22:99:6B:38:0F:D6:38:AA:93:B5:58:8E:E0
Signature algorithm name: SHA256withRSA
Subject Public Key Algorithm: 2048-bit RSA key
Version: 3

Extensions: 

#1: ObjectId: 2.5.29.14 Criticality=false
SubjectKeyIdentifier [
KeyIdentifier [
0000: 17 D4 A3 54 E4 0C DB CC   00 3E 1C 4D 74 B4 DE 55  ...T.....>.Mt..U
0010: D6 C9 CB 21                                        ...!
]
]



*******************************************
*******************************************


Alias name: alias1
Creation date: Apr 25, 2019
Entry type: PrivateKeyEntry
Certificate chain length: 1
Certificate[1]:
Owner: CN=Mallory Root, OU=Unknown, O=Example Corp, L=New York, ST=NY, C=US
Issuer: CN=Mallory Root, OU=Unknown, O=Example Corp, L=New York, ST=NY, C=US
Serial number: 2617e8fb
Valid from: Thu Apr 25 23:22:59 EDT 2019 until: Wed Jul 24 23:22:59 EDT 2019
Certificate fingerprints:
	 SHA1: DD:83:42:F3:AD:EB:DC:66:50:DA:7D:D7:59:32:9B:31:0C:E0:90:B9
	 SHA256: D9:3E:42:47:A1:DB:2F:00:46:F7:58:54:30:D1:83:F5:DD:C6:5D:8B:8B:6B:94:4A:34:B0:0D:D8:6F:7A:6E:B6
Signature algorithm name: SHA256withRSA
Subject Public Key Algorithm: 2048-bit RSA key
Version: 3

Extensions: 

#1: ObjectId: 2.5.29.14 Criticality=false
SubjectKeyIdentifier [
KeyIdentifier [
0000: 98 53 CF EF 77 36 02 4D   63 83 D7 4F 06 EF 09 CA  .S..w6.Mc..O....
0010: 41 92 6D 92                                        A.m.
]
]



*******************************************
*******************************************
```

That's a mess. We'd like to extract specific information about the keys in the keystore; specifically:

- The owner
- The issuer
- The creation date
- The valid from/valid until dates

There are a few ways of approaching this problem (for example, one could have your playbook call out to `awk` to parse the `keytool` output and generate JSON data for Ansible to consume), but a more robust, flexible, and often simpler way of dealing with something like this is to write a custom filter plugin in Python.

## What is a filter plugin?

A filter plugin defines one or more Python functions that can be used in Jinja2 templating expressions (using the `|` filter operator).  A filter function receives one mandatory argument (the value to the left of the `|`) and zero or more additional positional and/or keyword arguments, performs some transformation on the input data, and returns the result.

For example, there is a `unique` filter, which takes a list and returns a new list consisting of only unique values. If we had a list of names and wanted to eliminiate duplicates, we might use something like this:


```yaml
- set_fact:
    unique_names: "{{ ['alice', 'bob', 'alice', 'mallory', 'bob', 'mallory']|unique }}" 
```

That would set `unique_names` to the list `['alice', 'bob', 'mallory']`.

## How do you write a filter plugin?

A filter plugin doesn't require much.  You'll need to create a Python module that defines a `FilterModule` class, and that class must have a method named `filters` that will return a dictionary that maps filter names to callables implementing the filter.  For example, if we want a filter named `upper` that would transform a string to upper-case, we could write:

```python
class FilterModule(object):
    def filters(self):
      return {'upper': lambda x: x.upper()}
```

If we wanted implement a version of the `unique` filter, it might look like this:

```python
def filter_unique(things):
  seen = set()
  unique_things = []

  for thing in things:
    if thing not in seen:
      seen.add(thing)
      unique_things.append(thing)

  return unique_things


class FilterModule(object):
    def filters(self):
      return {'unique': filter_unique}
```

We need to put the new module in a directory named `filter_plugins` that is adjacent to our playbook. If we were to place the `upper` filter module in, say, `filter_plugins/upper.py`, we could then add a task like this to our playbook:

```yaml
- debug:
    msg: "{{ 'this is a test'|upper }}"
```

And get this output:

```
TASK [debug] **********************************************************************************
ok: [localhost] => {
    "msg": "THIS IS A TEST"
}
```

## Parsing keytool output

Our `keytool` filter is only a little bit more complicated:

```python
#!/usr/bin/python


def filter_keys_to_list(v):
    key_list = []
    key = {}
    found_start = False

    # iterate over lines of output from keytool
    for line in v.splitlines():
        # Discard any lines that don't look like "key: value" lines
        if ': ' not in line:
            continue

        # Look for "Alias name" at the beginning of a line to identify
        # the start of a new key.
        if line.startswith('Alias name'):
            found_start = True

            # If we have already collected data on a key, append that to
            # the list of keys.
            if key:
                key_list.append(key)
                key = {}

        # Read the next line if we haven't found the start of a key
        # yet.
        if not found_start:
            continue

        # Split fields and values into dictionary items.
        field, value = line.split(': ', 1)
        if field in ['Alias name', 'Owner', 'Issuer', 'Creation date']:
            key[field] = value
        elif field == 'Valid from':
            key['Valid from'], key['Valid until'] = value.split(' until: ')

    # Append the final key.
    if key:
        key_list.append(key)

    return key_list


class FilterModule(object):
    filter_map = {
        'keys_to_list': filter_keys_to_list,
    }

    def filters(self):
        return self.filter_map

```

The logic here is fairly simple:

- Iterate over the lines in the output from `keytool`.
- Look for "Alias name" at the beginning of a line to identify
  the start of key data.
- Split lines on `: ` into field names and values.
- Assemble a dictionary from selected fields.
- Append the dictionary to a list and repeat.

Using it makes for a clear and simple playbook:


```yaml
- set_fact:
    key_list: "{{ keytool.stdout|keys_to_list }}"
```

## More information

- [Playbook and filter plugin referenced in this article](https://github.com/larsks/blog-2019-04-25-filter-plugins)
- [Ansible "Filters" documentation](https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters.html)
- [Existing filter plugins in Ansible](https://github.com/ansible/ansible/tree/devel/lib/ansible/plugins/filter)
