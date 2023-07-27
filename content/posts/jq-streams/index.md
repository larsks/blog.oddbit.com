---
categories: [tech]
title: Processing deeply nested JSON with jq streams
date: "2023-07-27"
tags:
  - jq
  - json
---

I [recently][] found myself wanting to perform a few transformations on a large [OpenAPI][] schema. In particular, I wanted to take the schema available from the `/openapi/v2` endpoint of a Kubernetes server and minimize it by (a) extracting a subset of the definitions and (b) removing all the `description` attributes.

[recently]: https://stackoverflow.com/a/76762619/147356
[openapi]: https://www.openapis.org/

The first task is relatively easy, since everything of interest exists at the same level in the schema. If I want one or more specific definitions, I can simply ask for those by key. For example, if I want the definition of a [`DeploymentConfig`][dc] object, I can run:

[dc]: https://docs.openshift.com/container-platform/4.13/rest_api/workloads_apis/deploymentconfig-apps-openshift-io-v1.html

```
jq '.definitions."com.github.openshift.api.apps.v1.DeploymentConfig"' < openapi.json
```

So simple! And so wrong! Because while that does extract the required definition, that definition is not self-contained: it refers to *other* definitions via [`$ref`][ref] pointers. The *real* solution would require code that parses the schema, resolves all the `$ref` pointers, and spits out a fully resolved schema. Fortunately, in this case we can get what we need by asking for schemas matching a few specific prefixes. Using `jq`, we can match keys against a prefix by:

[ref]: https://json-schema.org/understanding-json-schema/structuring.html#ref

- Using the `to_entries` filter to transform a dictionary into a list of `{"key": ..., "value": ...}` dictionaries, and then
- Using `select` with the `startswith` function to match specific keys, and finally
- Reconstructing the data with `from_entries`

Which looks like:

```
jq '[.definitions|to_entries[]|select(
  (.key|startswith("com.github.openshift.api.apps.v1.Deployment")) or
  (.key|startswith("io.k8s.apimachinery")) or
  (.key|startswith("io.k8s.api.core"))
)]|from_entries' < openapi.json
```

That works, but results in almost 500KB of output, which seems excessive. We could further reduce the size of the document by removing all the `description` elements, but here is where things get tricky: `description` attributes can occur throughout the schema hierarchy, so we can't use a simple path (`...|del(.value.description)` to remove them.

A simple solution is to use sed:

```
jq ... | sed '/"description"/d'
```

While normally I would never use `sed` for processing JSON, that actually works in this case: because we're first running the JSON document through `jq`, we can be confident about the formatting of the document being passed through `sed`, and anywhere the string `"description"` is contained in the value of an attribute the quotes will be escaped so we would see `\"description\"`.

We could stop here and things would be just fine...but I was looking for a way to perform the same operation in a structured fashion. What I really wanted was an equivalent to xpath's `//` operator (e.g., the path `//description` would find all `<description>` elements in a document, regardless of how deeply they were nested), but no such equivalent exists in `jq`. Then I came across the `tostream` filter, which is really neat: it transforms a JSON document into a sequence of `[path, leaf-value]` nodes (or `[path]` to indicate the end of an array or object).

That probably requires an example. The document:

```
{
  "name": "gizmo",
  "color": "red",
  "count": {
    "local": 1,
    "warehouse": 3
  }
}
```

When converted into a stream becomes:

```
[["name"],"gizmo"]
[["color"],"red"]
[["count","local"],1]
[["count","warehouse"],3]
[["count","warehouse"]]
[["count"]]
```

You can see how each attribute is represented by a tuple. For example, for `.count.local`, the first element of the tuple is `["count", "local"]`, representing that path to the value in the document, and the second element is the value itself (`1`). The "end" of an object is indicated by a 1-tuple (`[path]`), such as `[["count"]]` at the end of this example.

If we convert the OpenAPI schema to a stream, we'll end up with nodes for the `description` attributes that look like this:

```
[
  [
    "com.github.openshift.api.apps.v1.DeploymentCause",
    "properties",
    "imageTrigger",
    "description"
  ],
  "ImageTrigger contains the image trigger details, if this trigger was fired based on an image change"
]
```

To match those, we need to look for nodes for which the last element of the first item is `description`. That is:

```
...|tostream|select(.[0][-1]=="description"))
```

Of course, we don't want to *select* those nodes; we want to delete them:

```
...|tostream|del(select(.[0][-1]=="description")))
```

And lastly, we need to feed the result back to the `fromstream` function to reconstruct the document. Putting all of that together -- and populating some required top-level keys so that we end up with a valid OpenAPI schema -- looks like this:

```
jq '
  fromstream(
    {
      "swagger": .swagger,
      "definitions": [
      .definitions|to_entries[]|select(
        (.key|startswith("com.github.openshift.api.apps.v1.Deployment")) or
        (.key|startswith("io.k8s.apimachinery")) or
        (.key|startswith("io.k8s.api.core"))
      )]|from_entries
    }|tostream|del(select(.[0][-1]=="description"))|select(. != null)
  )
'
```

In my environment, this reduces the size of the resulting file from about 500KB to around 175KB.
