---
categories: [tech]
aliases: ["/2018/02/26/grouping-aggregation-queries-i/"]
title: Grouping aggregation queries in Gnocchi 4.0.x
date: "2018-02-26"
tags:
- openstack
- gnocchi
- metrics
---

In this article, we're going to ask Gnocchi (the OpenStack telemetry
storage service) how much memory was used, on average, over the course
of each day by each project in an OpenStack environment.

## Environment

I'm working with an OpenStack "Pike" deployment, which means I have
Gnocchi 4.0.x. More recent versions of Gnocchi (4.1.x and later) have
a new aggregation API called [dynamic aggregates][], but that isn't
available in 4.0.x so in this article we'll be using the legacy
`/v1/aggregations` API.

[dynamic aggregates]: https://gnocchi.xyz/rest.html#dynamic-aggregates

## The Gnocchi data model

In Gnocchi, named metrics are associated with *resources*. A
*resource* corresponds to an object in OpenStack, such as a Nova
instance, or a Neutron network, etc. Metrics on a resource are
created dynamically and depend entirely on which metrics you are
collecting with Ceilometer and delivering to Gnocchi, and two
different resources of the same resource type may have different sets
of metrics.

The list of metrics available from OpenStack is available in the
[telemetry documentation][metrics]. The [metrics available for Nova
servers][compute-metrics] include statistics on cpu utilization,
memory utilization, disk read/write operations, network traffic, and
more.

[metrics]: https://docs.openstack.org/ceilometer/latest/admin/telemetry-measurements.html
[compute-metrics]: https://docs.openstack.org/ceilometer/latest/admin/telemetry-measurements.html#openstack-compute

In this example, we're going to look at the `memory.usage` metric.

## Building a query

The amount of memory used is available in the `memory.usage` metric
associated with each `instance` resource. We're using the legacy
`/v1/aggregations` API, so the request url will initially look like:

    /v1/aggregation/resource/instance/metric/memory.usage

We need to specify which granularity we want to fetch. We're using
the `low` archive policy from the default Gnocchi configuration which
means we only have one option (metrics are aggregated into 5 minute
intervals). We use the `granularity` parameter to tell Gnocchi which
granularity we want:

    .../metric/memory.usage?granularity=300

We want the average utilization, so that means:

    .../metric/memory.usage?granularity=300&aggregation=mean

We'd like to limit this to the past 30 days of data, so we'll add an
appropriate `start` parameter. There are various ways of specifying
time in Gnocchi, documented in the [Timestamps][] section of the docs.
Specifying "30 days ago" is as simple as: `start=-30+days`. So our
request now looks like:

[timestamps]: https://gnocchi.xyz/rest.html#timestamp-format

    .../metric/memory.usage?granularity=300&aggregation=mean&start=-30+days

We have values at 5 minute intervals, but we would like daily
averages, so we'll need to use the [resample][] parameter to ask
Gnocchi to reshape the data for us. The argument to `resample` is a
time period specified as a number of seconds; since we want daily
averages, that means `resample=86400`:

[resample]: https://gnocchi.xyz/rest.html#resample

    .../metric/memory.usage?granularity=300&aggregation=mean&start=-30+days&resample=86400

We want to group the results by project, which means we'll need the
`groupby` parameter. Instances (and most other resources) store this
information in the `project_id` attribute, so `groupby=project_id`:

    .../metric/memory.usage?granularity=300&aggregation=mean&start=-30+days&resample=86400&groupby=project_id

Lastly, not all metrics will have measurements covering the same
period. If we were to try the query as we have it right now, we would
probably see:

    400 Bad Request

    The server could not comply with the request since it is either
    malformed or otherwise incorrect.

    One of the metrics being aggregated doesn't have matching
    granularity: Metrics <list of metrics here>...can't be aggregated:
    No overlap

Gnocchi provides a `fill` parameter to indicate what should happen
with missing data. In Gnocchi 4.0.x, the options are `fill=0`
(replace missing data with `0`) and `fill=null` (compute the
aggregation using only available data points). Selecting `fill=0` gets
us:

    .../metric/memory.usage?granularity=300&aggregation=mean&start=-30+days&resample=86400&groupby=project_id&fill=0

That should give us the results we want. The return value from that
query looks something like this:

    [
        {
            "group": {
                "project_id": "00a8d5e942bb442b86733f0f92280fcc"
            },
            "measures": [
                [
                    "2018-02-14T00:00:00+00:00",
                    86400.0,
                    2410.014338235294
                ],
                [
                    "2018-02-15T00:00:00+00:00",
                    86400.0,
                    2449.4921970791206
                ],
                .
                .
                .
        {
            "group": {
                "project_id": "03d2a1de5b2342d78d14e5294a81e0b0"
            },
            "measures": [
                [
                    "2018-02-14T00:00:00+00:00",
                    86400.0,
                    381.0
                ],
                [
                    "2018-02-15T00:00:00+00:00",
                    86400.0,
                    380.99004975124376
                ],
                [
                    "2018-02-16T00:00:00+00:00",
                    86400.0,
                    380.99305555555554
                ],
                .
                .
                .

## Authenticating to Gnocchi

Since we're using Gnocchi as part of an OpenStack deployment, we'll
be authenticating to Gnocchi using a Keystone token. Let's take a
look at how you could do that from the command line using `curl`.

### Acquiring a token

You can acquire a token using the `openstack token issue` command,
which will produce output like:

    +------------+------------------------------------------------------------------------+
    | Field      | Value                                                                  |
    +------------+------------------------------------------------------------------------+
    | expires    | 2018-02-26T23:09:36+0000                                               |
    | id         | ...                                                                    |
    | project_id | c53c18b2d29641e0877bbbd8d87f8267                                       |
    | user_id    | 533ad9ab4fed403fb98f1ffc2f2b4436                                       |
    +------------+------------------------------------------------------------------------+

While it is possible to parse that with, say, `awk`, it's not
really designed to be machine readable. We can get just the token
value by instead calling:

    openstack token issue -c id -f value

We should probably store that in a variable:

    TOKEN=$(openstack token issue -c id -f value)

### Querying Gnocchi

In order to make our command line shorter, let's set `ENDPOINT` to the
URL of our Gnocchi endpoint:

    ENDPOINT=http://cloud.example.com:8041/v1

We'll pass the Keystone token in the `X-Auth-Token` header. Gnocchi
is expecting a JSON document body as part of this request (you can use
that to specify a filter; see the [API documentation][] for details),
so we need to both set a `Content-type` header and provide at least an
empty JSON object. That makes our final request look like:

    curl \
      -H "X-Auth-Token: $TOKEN" \
      -H "Content-type: application/json" \
      -d "{}" \
      "$ENDPOINT/aggregation/resource/instance/metric/memory.usage?granularity=300&aggregation=mean&start=-30+days&resample=86400&groupby=project_id&fill=0"

[api documentation]: https://gnocchi.xyz/rest.html
