---
categories:
- tech
date: '2021-02-27'
draft: false
tags:
- git
- graphviz
title: Tools for writing about Git

---

I sometimes find myself writing articles or documentation about
[git][], so I put together a couple of terrible hacks for generating
reproducible histories and pretty graphs of those histories.

[git]: https://git-scm.org

## git synth

The [`git synth`][git-synth] command reads a [YAML][] description of a
repository and executes the necessary commands to reproduce that
history. It allows you set the name and email address of the author
and committer as well as static date, so you every time you generate
the repository you can identical commit ids.

[yaml]: https://yaml.org/
[git-synth]: https://github.com/larsks/git-snippets/blob/master/git-synth

## git dot

The [`git dot`][git-dot] command generates a representation of a repository
history in the [dot][] language, and uses [Graphviz][] to render those
into diagrams.

[dot]: https://en.wikipedia.org/wiki/DOT_(graph_description_language)
[graphviz]: https://graphviz.org/
[git-dot]: https://github.com/larsks/git-snippets/blob/master/git-dot

## Putting it together

For example, the following history specification:

```
<!-- include examplerepo.yml -->
```

When applied with `git synth`:

```
$ git synth -r examplerepo examplerepo.yml
```

Will generate the following repository:

```
$ git -C examplerepo log --graph --all --decorate --oneline
* 28f7b38 (HEAD -> master) H
| * 93e1d18 (topic2) G
| * 3ef811d F
| * 973437c (topic1) E
| * 2c0bd1c D
|/  
* cabdedf C
* a5cbd99 B
* d98f949 A
```

We can run this `git dot` command line:

```
$ git -C examplerepo dot -m -g branch --rankdir=RL
```

To produce the following `dot` description of the history:


```
<!-- include examplerepo.dot -->
```

Running that through the `dot` utility (`dot -Tsvg -o repo.svg
repo.dot`) results in the following diagram:

```graphviz
<!-- include examplerepo.dot -->
```

## Where are these wonders?

Both tools live in my [git-snippets][] repository, which is a motley
collection of shells scripts, python programs, and other utilities for
interacting with `git`.

It's all undocumented and uninstallable, but if there's interest in
either of these tools I can probably find the time to polish them up a
bit.

[git-snippets]: https://github.com/larsks/git-snippets
