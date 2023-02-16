---
aliases:
- /2015/11/17/installing-pyspatialite-on-fedora/
- /post/2015-11-17-installing-pyspatialite-on-fedora
categories:
- tech
date: '2015-11-17'
tags:
- fedora
- gis
title: Installing pyspatialite on Fedora
---

If you should find yourself wanting to install [pyspatialite][] on
Fedora -- perhaps because you want to use the [Processing plugin][]
for [QGIS][] -- you will first need to install the following
dependencies:

[pyspatialite]: https://github.com/lokkju/pyspatialite
[processing plugin]: https://plugins.qgis.org/plugins/processing/
[qgis]: http://www.qgis.org/

- `gcc`
- `python-devel`
- `sqlite-devel`
- `geos-devel`
- `proj-devel`
- `python-pip`
- `redhat-rpm-config`

After which you can install `pyspatialite` using `pip` by running:

    CFLAGS=-I/usr/include pip install pyspatialite

At this point, you should be able to use the "Processing" plugin.