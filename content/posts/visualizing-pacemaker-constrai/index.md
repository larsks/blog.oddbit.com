---
aliases:
- /2015/02/24/visualizing-pacemaker-constraints/
- /post/2015-02-24-visualizing-pacemaker-constraints
categories:
- tech
date: '2015-02-24'
tags:
- pacemaker
- visualization
title: Visualizing Pacemaker resource constraints
---

If a picture is worth a thousand words, then code that generates
pictures from words is worth...uh, anyway, I wrote a script that
produces [dot][] output from Pacemaker start and colocation
constraints:

   https://github.com/larsks/pacemaker-tools/

You can pass this output to [graphviz][] to create visualizations of
your Pacemaker resource constraints.

[dot]: http://en.wikipedia.org/wiki/DOT_%28graph_description_language%29
[graphviz]: http://www.graphviz.org/

The `graph-constraints.py` script in that repository consumes the
output of `cibadmin -Q` and can produce output for either start
constraints (`-S`, the default) or colocation constraints (`-C`).

Given a document like [this][cib.xml], if you run:

    cibadmin -Q | 
    python graph-constraints.py -o cib.svg

You get a graph like [this][cib.svg]:

{{< figure
src="cib.svg"
link="cib.svg"
width="800"
>}}

Nodes are colored by their tag (so, `primitive`, `clone`, etc).

[cib.xml]: cib.xml
[cib.svg]: cib.svg
