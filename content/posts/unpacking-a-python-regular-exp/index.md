---
categories: [tech]
title: "Unpacking a Python regular expression"
date: "2019-05-07T10:00:00Z"
tags:
- "python"
- "stackexchange"
---

I recently answered [a question][] from [Harsha Nalore][] on [StackOverflow][] that involved using Ansible to extract the output of a command sent to a BigIP device of some sort. My solution -- which I claim to be functional, but probably not optimal -- involved writing an [Ansible][] filter module to parse the output. That filter made use of a complex-looking regular expression. Harsha asked for some details on that regular expression works, and the existing StackOverflow answer didn't really seem the write place for that: so, here we are.

The output in question looks like this:

```
gtm wideip a wideip {
    description wideip
    pool-lb-mode topology
    pools {
        test1-pool {
            order 1
        }
        test2-pool {
            order 0
        }
    }
}
```

The goal is to return a list of pool names. You can see the complete solution in [my answer][]; for the purposes of this post we're interesting in the following two regular expressions:

```python
re_pools = re.compile('''
gtm \s+ wideip \s+ a \s+ (\S+) \s+ { \s+
(?P<parameters>(\S+ \s+ \S+ \s+)*)
pools \s+ { \s+ (?P<pools>
(?:
\S+ \s+ {  \s+
[^}]* \s+
} \s+
)+ \s+
)
}
''', flags=re.VERBOSE)

re_pool = re.compile('''
(\S+) \s+ { \s+ [^}]* \s+ } \s+
''', flags=re.VERBOSE)
```

# VERBOSE mode

The first thing to note is that I'm using `VERBOSE` syntax for both of these expressions. That means that whitespace must be included explicitly in the expression. That's what all of those `\s+` markers are -- that means "any white space character, one or more times". For example, consider the following simple expression:

```python
>>> re.match('this is a test', 'this is a test')
```

The pattern matches the string just fine. But if we were to enable the `VERBOSE` flag, the pattern would no longer match:

```python
>>> re.match('this is a test', 'this is a test', flags=re.VERBOSE)
```

We would instead need to write it like this:

```python
>>> re.match('this \s is \s a \s test', 'this is a test', flags=re.VERBOSE)
```

The advantage to `VERBOSE` mode is that you can split your regular expression across multiple lines for legibility:

```python
>>> re.match('''
... this \s
... is \s
... a \s
... test''', 'this is a test', flags=re.VERBOSE)
```

## Capture groups

In order to make it easier to extract information from the results of a match, I'm using named capture groups. A "capture group" is a part of the expression inside parentheses that can be extracted from the resulting match object.  Unnamed groups can be extracted using their index.  If we wanted to match the phrase `this is a <noun>`, rather than `this is a test`, and we wanted to extract the noun, we might write something like this:

```python
>>> re_example = re.compile('this is a (\S+)')
>>> match = re_example.match('this is a frog')
>>> match.groups()
('frog',)
>>> match.group(1)
'frog'
```

The expression `(\S+)` is a capture group that will match any string of non-whitespace characters.  This works fine for a simple expression, but keeping the index straight in a complex expression can be difficult.  This is where named capture groups become useful.  We could rewrite the above like this:

```python
>>> re_example = re.compile('this is a (?P<noun>\S+)')
>>> match = re_example.match('this is a frog')
>>> match.groupdict()
{'noun': 'frog'}
>>> match.group('noun')
'frog'
```

## Non-capture groups

Sometimes, you want to group part of a regular expression in a way that does not result in another capture group.  This is what the `(?: ...)` expression is for.  For example, we we were to write:

```python
>>> re_example = re.compile('this (?:is|was) a (?P<noun>\S+)')
```

Then we could match the phrase `this is a test` or `this was a test`, but we would still only have a single capture group:

```python
>>> match = re_example.match('this is a test')
>>> match.groupdict()
{'noun': 'test'}
```

## Putting it all together

With all that in mind, let's take a look at the regular expression in my answer:

```python
re_pools = re.compile('''
gtm \s+ wideip \s+ a \s+ (\S+) \s+ { \s+
(?P<parameters>(\S+ \s+ \S+ \s+)*)
pools \s+ { \s+ (?P<pools>
(?:
\S+ \s+ {  \s+
[^}]* \s+
} \s+
)+ \s+
)
}
''', flags=re.VERBOSE)
```

The first line matches `gtm wideip a <something> {`:

    gtm \s+ wideip \s+ a \s+ (\S+) \s+ { \s+

Next, we match the `<key> <value>` part of the output, which looks like this:

    description wideip
    pool-lb-mode topology

With this expression:

     (?P<parameters>(\S+ \s+ \S+ \s+)*)

That is a named capture group ("parameters") that matches the expression `(\S+ \s+ \S+ \s+)` zero or more times (`*`). Since `\S+` means "a string of non-whitespace characters" and `\s+` means "a string of whitespace characters", this correctly matches that part of the output.

Next, we match the entire `pools {...}` part of the output with this expression:

    pools \s+ { \s+ (?P<pools>
    (?:
    \S+ \s+ {  \s+
    [^}]* \s+
    } \s+
    )+ \s+
    )

That creates a named capture group ("pools") that looks for one or more occurrences of the pattern:

    \S+ \s+ {  \s+
    [^}]* \s+
    } \s+

The first line will match a string like `test1-pool1 {`.  The next line matches any sequence of characters that are not `}`, so that gathers up everthing between `test1-pool {` and the closing `}`.  Because we have the entire thing wrapped in `(?: ...)+`, we are looking for one or more matches of that sub-expression, which gathers up all of the pool definitions.

Finally we match the closing brace:

    }

When that expression matches, we end up with a match object that has a `pools` match group that will look like this:

```python
>>> print(match.group('pools'))
test1-pool {
            order 1
        }
        test2-pool {
            order 0
        }

```

We now use a much simpler regular expression to extract the pool names from that content:

```python
re_pool = re.compile('''
(\S+) \s+ { \s+ [^}]* \s+ } \s+
''', flags=re.VERBOSE)
```

That has a single capture group (`(\S+)`) that will match the pool name; the remainder of the expression takes care of matching the `{ <anythingthing not '}'> }` part.  We use `re.findall` to get *all* of the matches in one go:

```python
>>> re_pool.findall(match.group('pools'))
['test1-pool', 'test2-pool']
```

And that's it!

## For more information

For more information on Python regular expressions:

- The documentation for the [re](https://docs.python.org/3/library/re.html) module.
- The [Regular expression HOWTO](https://docs.python.org/3/howto/regex.html)

[a question]: https://stackoverflow.com/q/55965819/147356
[stackoverflow]: https://stackoverflow.com/
[ansible]: https://ansible.com/
[harsha nalore]: https://stackoverflow.com/users/7738974/harsha-nalore
[my answer]: https://stackoverflow.com/a/55970019/147356
