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
- set:
    date: "2021-01-01"
    name: Fake Person
    email: fake@example.com
- branch:
    name: master
    actions:
      - commit:
          message: A
      - commit:
          message: B
      - commit:
          message: C
      - branch:
          name: topic1
          actions:
            - commit:
                message: D
            - commit:
                message: E
            - branch:
                name: topic2
                actions:
                  - commit:
                      message: F
                  - commit:
                      message: G
      - commit:
          message: H

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
digraph git {
	graph [rankdir=RL]
	node [shape=circle]
	{
		node [group=master_commits]
		"28f7b382a5" [label=H tooltip="28f7b382a52ac53f86314e5d608ebafd66de6c44"]
		cabdedff95 [label=C tooltip=cabdedff957f7dec15f365e7c29eaead9930d618]
		a5cbd99954 [label=B tooltip=a5cbd999545aeabc2e102a845aeb0466f01454a2]
		d98f949840 [label=A tooltip=d98f94984057d760066ba0b300ab4930497bcba6]
	}
	{
		node [group=topic1_commits]
		"973437cb00" [label=E tooltip="973437cb007d2a69d6564fd7b30f3e8c347073c2"]
		"2c0bd1c1df" [label=D tooltip="2c0bd1c1dfe9f76cd18b37bb0bc995e449e0094b"]
	}
	{
		node [group=topic2_commits]
		"93e1d18862" [label=G tooltip="93e1d18862102e044a4ec46bb189f5bca9ba0e05"]
		"3ef811d426" [label=F tooltip="3ef811d426c09be792a0ff6564eca82a7bd105a9"]
	}
	{
		node [color=black fontcolor=white group=heads shape=box style=filled]
		master
		topic1
		topic2
	}
	{
		edge [style=dashed]
		topic2 -> "93e1d18862"
		topic1 -> "973437cb00"
		master -> "28f7b382a5"
	}
	a5cbd99954 -> d98f949840
	"3ef811d426" -> "973437cb00"
	"973437cb00" -> "2c0bd1c1df"
	cabdedff95 -> a5cbd99954
	"28f7b382a5" -> cabdedff95
	"2c0bd1c1df" -> cabdedff95
	"93e1d18862" -> "3ef811d426"
}
```

Running that through the `dot` utility (`dot -Tsvg -o repo.svg
repo.dot`) results in the following diagram:

{{< figure src="gen-094ef3d69a7692db2cdee8e04869e8f98bdd237b.svg" link="gen-094ef3d69a7692db2cdee8e04869e8f98bdd237b.txt" >}}

## Where are these wonders?

Both tools live in my [git-snippets][] repository, which is a motley
collection of shells scripts, python programs, and other utilities for
interacting with `git`.

It's all undocumented and uninstallable, but if there's interest in
either of these tools I can probably find the time to polish them up a
bit.

[git-snippets]: https://github.com/larsks/git-snippets
