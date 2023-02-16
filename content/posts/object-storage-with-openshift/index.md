---
categories:
- tech
date: '2021-02-10'
filename: 2021-02-10-object-storage-with-openshift.md
stub: object-storage-with-openshift
tags:
- openshift
- openshift-ocs
- s3
- kubernetes
title: Object storage with OpenShift Container Storage

---

[OpenShift Container Storage][ocs] (OCS) from Red Hat deploys Ceph in your
OpenShift cluster (or allows you to integrate with an external Ceph
cluster). In addition to the file- and block- based volume services
provided by Ceph, OCS includes two S3-api compatible object storage
implementations.

[ocs]: https://www.redhat.com/en/technologies/cloud-computing/openshift-container-storage

The first option is the [Ceph Object Gateway][radosgw] (radosgw),
Ceph's native object storage interface. The second option called the
"[Multicloud Object Gateway][]", which is in fact a piece of software
named [Noobaa][], a storage abstraction layer that was [acquired by
Red Hat][] in 2018.  In this article I'd like to demonstrate how to
take advantage of these storage options.

[radosgw]: https://docs.ceph.com/en/latest/radosgw/
[noobaa]: https://www.noobaa.io/
[acquired by red hat]: https://www.redhat.com/en/blog/faq-red-hat-acquires-noobaa
[multicloud object gateway]: https://www.openshift.com/blog/introducing-multi-cloud-object-gateway-for-openshift

## What is object storage?

The storage we interact with regularly on our local computers is
block storage: data is stored as a collection of blocks on some sort
of storage device. Additional layers -- such as a filesystem driver --
are responsible for assembling those blocks into something useful.

Object storage, on the other hand, manages data as objects: a single
unit of data and associated metadata (such as access policies). An
object is identified by some sort of unique id. Object storage
generally provides an API that is largely independent of the physical
storage layer; data may live on a variety of devices attached to a
variety of systems, and you don't need to know any of those details in
order to access the data.

The most well known example of object storage service Amazon's
[S3][] service ("Simple Storage Service"), first introduced in 2006.
The S3 API has become a de-facto standard for object storage
implementations. The two services we'll be discussing in this article
provide S3-compatible APIs.

[s3]: https://aws.amazon.com/s3/

## Creating buckets

The fundamental unit of object storage is called a "bucket".

Creating a bucket with OCS works a bit like creating a [persistent
volume][], although instead of starting with a `PersistentVolumeClaim`
you instead start with an `ObjectBucketClaim` ("`OBC`"). An `OBC`
looks something like this when using RGW:

[persistent volume]: https://kubernetes.io/docs/concepts/storage/persistent-volumes/

```yaml
apiVersion: objectbucket.io/v1alpha1
kind: ObjectBucketClaim
metadata:
  name: example-rgw
spec:
  generateBucketName: example-rgw
  storageClassName: ocs-storagecluster-ceph-rgw
```

Or like this when using Noobaa (note the different value for
`storageClassName`):

```yaml
apiVersion: objectbucket.io/v1alpha1
kind: ObjectBucketClaim
metadata:
  name: example-noobaa
spec:
  generateBucketName: example-noobaa
  storageClassName: openshift-storage.noobaa.io
```

With OCS 4.5, your out-of-the-box choices for `storageClassName` will be
`ocs-storagecluster-ceph-rgw`, if you choose to use Ceph Radosgw, or
`openshift-storage.noobaa.io`, if you choose to use the Noobaa S3 endpoint.

Before we continue, I'm going to go ahead and create these resources
in my OpenShift environment. To do so, I'm going to use [Kustomize][]
to deploy the resources described in the following `kustomization.yml`
file:

[kustomize]: https://kustomize.io/

```yaml
namespace: oddbit-ocs-example

resources:
  - obc-noobaa.yml
  - obc-rgw.yml
```

Running `kustomize build | oc apply -f-` from the directory containing
this file populates the specified namespace with the two
`ObjectBucketClaims` mentioned above:

```sh
$ kustomize build | oc apply -f-
objectbucketclaim.objectbucket.io/example-noobaa created
objectbucketclaim.objectbucket.io/example-rgw created

```

Verifying that things seem healthy:

```sh
$ oc get objectbucketclaim
NAME             STORAGE-CLASS                 PHASE   AGE
example-noobaa   openshift-storage.noobaa.io   Bound   2m59s
example-rgw      ocs-storagecluster-ceph-rgw   Bound   2m59s

```

Each `ObjectBucketClaim` will result in a OpenShift creating a new
`ObjectBucket` resource (which, like `PersistentVolume` resources, are
not namespaced). The `ObjectBucket` resource will be named
`obc-<namespace-name>-<objectbucketclaim-name>`.

```sh
$ oc get objectbucket obc-oddbit-ocs-example-example-rgw obc-oddbit-ocs-example-example-noobaa
NAME                                    STORAGE-CLASS                 CLAIM-NAMESPACE      CLAIM-NAME       RECLAIM-POLICY   PHASE   AGE
obc-oddbit-ocs-example-example-rgw      ocs-storagecluster-ceph-rgw   oddbit-ocs-example   example-rgw      Delete           Bound   67m
obc-oddbit-ocs-example-example-noobaa   openshift-storage.noobaa.io   oddbit-ocs-example   example-noobaa   Delete           Bound   67m
```

Each `ObjectBucket` resource corresponds to a bucket in the selected
object storage backend.

Because buckets exist in a flat namespace, the OCS documentation
recommends always using `generateName` in the claim, rather than
explicitly setting `bucketName`, in order to avoid unexpected
conflicts. This means that the generated buckets will have a named
prefixed by the value in `generateName`, followed by a random string:

```sh
$ oc get objectbucketclaim example-rgw -o jsonpath='{.spec.bucketName}'
example-rgw-425d7193-ae3a-41d9-98e3-9d07b82c9661

$ oc get objectbucketclaim example-noobaa -o jsonpath='{.spec.bucketName}'
example-noobaa-2e087028-b3a4-475b-ae83-a4fa80d9e3ef

```

Along with the bucket itself, OpenShift will create a `Secret` and a
`ConfigMap` resource -- named after your `OBC` -- with the metadata
necessary to access the bucket.


The `Secret` contains AWS-style credentials for authenticating to the
S3 API:

```sh
$ oc get secret example-rgw -o yaml | oc neat
apiVersion: v1
data:
  AWS_ACCESS_KEY_ID: ...
  AWS_SECRET_ACCESS_KEY: ...
kind: Secret
metadata:
  labels:
    bucket-provisioner: openshift-storage.ceph.rook.io-bucket
  name: example-rgw
  namespace: oddbit-ocs-example
type: Opaque

```

(I'm using the [neat][] filter here to remove extraneous metadata that
OpenShift returns when you request a resource.)

[neat]: https://github.com/itaysk/kubectl-neat

The `ConfigMap` contains a number of keys that provide you (or your code)
with the information necessary to access the bucket. For the RGW
bucket:

```sh
$ oc get configmap example-rgw -o yaml | oc neat
apiVersion: v1
data:
  BUCKET_HOST: rook-ceph-rgw-ocs-storagecluster-cephobjectstore.openshift-storage.svc.cluster.local
  BUCKET_NAME: example-rgw-425d7193-ae3a-41d9-98e3-9d07b82c9661
  BUCKET_PORT: "80"
  BUCKET_REGION: us-east-1
kind: ConfigMap
metadata:
  labels:
    bucket-provisioner: openshift-storage.ceph.rook.io-bucket
  name: example-rgw
  namespace: oddbit-ocs-example
```

And for the Noobaa bucket:

```sh
$ oc get configmap example-noobaa -o yaml | oc neat
apiVersion: v1
data:
  BUCKET_HOST: s3.openshift-storage.svc
  BUCKET_NAME: example-noobaa-2e087028-b3a4-475b-ae83-a4fa80d9e3ef
  BUCKET_PORT: "443"
kind: ConfigMap
metadata:
  labels:
    app: noobaa
    bucket-provisioner: openshift-storage.noobaa.io-obc
    noobaa-domain: openshift-storage.noobaa.io
  name: example-noobaa
  namespace: oddbit-ocs-example

```

Note that `BUCKET_HOST` contains the internal S3 API endpoint. You won't be
able to reach this from outside the cluster. We'll tackle that in just a
bit.

## Accessing a bucket from a pod

The easiest way to expose the credentials in a pod is to map the keys
from both the `ConfigMap` and `Secret` as environment variables using
the `envFrom` directive, like this:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: bucket-example
spec:
  containers:
    - image: myimage
      env:
        - name: AWS_CA_BUNDLE
          value: /run/secrets/kubernetes.io/serviceaccount/service-ca.crt
      envFrom:
        - configMapRef:
            name: example-rgw
        - secretRef:
            name: example-rgw
      [...]
```

Note that we're also setting `AWS_CA_BUNDLE` here, which you'll need
if the internal endpoint referenced by `$BUCKET_HOST` is using SSL.

Inside the pod, we can run, for example, `aws` commands as long as we
provide an appropriate s3 endpoint. We can inspect the value of
`BUCKET_PORT` to determine if we need `http` or `https`:

```sh
$ [ "$BUCKET_PORT" = 80 ] && schema=http || schema=https
$ aws s3 --endpoint $schema://$BUCKET_HOST ls
2021-02-10 04:30:31 example-rgw-8710aa46-a47a-4a8b-8edd-7dabb7d55469

```

Python's `boto3` module can also make use of the same environment
variables:

```python
>>> import boto3
>>> import os
>>> bucket_host = os.environ['BUCKET_HOST']
>>> schema = 'http' if os.environ['BUCKET_PORT'] == '80' else 'https'
>>> s3 = boto3.client('s3', endpoint_url=f'{schema}://{bucket_host}')
>>> s3.list_buckets()['Buckets']
[{'Name': 'example-noobaa-...', 'CreationDate': datetime.datetime(...)}]

```

## External connections to S3 endpoints

External access to services in OpenShift is often managed via
[routes][].  If you look at the routes available in your
`openshift-storage` namespace, you'll find the following:

[routes]: https://docs.openshift.com/enterprise/3.0/architecture/core_concepts/routes.html

```sh
$ oc -n openshift-storage get route
NAME          HOST/PORT                                               PATH   SERVICES                                           PORT         TERMINATION   WILDCARD
noobaa-mgmt   noobaa-mgmt-openshift-storage.apps.example.com          noobaa-mgmt                                        mgmt-https   reencrypt     None
s3            s3-openshift-storage.apps.example.com                   s3                                                 s3-https     reencrypt     None

```

The `s3` route provides external access to your Noobaa S3 endpoint.
You'll note that in the list above there is no route registered for
radosgw[^ocs46]. There is a service registered for Radosgw named
`rook-ceph-rgw-ocs-storagecluster-cephobjectstore`, so we
can expose that service to create an external route by running
something like:

```sh
oc create route edge rgw --service rook-ceph-rgw-ocs-storagecluster-cephobjectstore
```

This will create a route with "edge" encryption (TLS termination is
handled by the default ingress router):

```sh
$ oc -n openshift storage get route
NAME          HOST/PORT                                               PATH   SERVICES                                           PORT         TERMINATION   WILDCARD
noobaa-mgmt   noobaa-mgmt-openshift-storage.apps.example.com          noobaa-mgmt                                        mgmt-https   reencrypt     None
rgw           rgw-openshift-storage.apps.example.com                  rook-ceph-rgw-ocs-storagecluster-cephobjectstore   http         edge          None
s3            s3-openshift-storage.apps.example.com                   s3                                                 s3-https     reencrypt     None

```

[^ocs46]: note that this may have changed in the recent OCS 4.6
  release

## Accessing a bucket from outside the cluster

Once we know the `Route` to our S3 endpoint, we can use the
information in the `Secret` and `ConfigMap` created for us when we
provisioned the storage. We just need to replace the `BUCKET_HOST`
with the hostname in the route, and we need to use SSL over port 443
regardless of what `BUCKET_PORT` tells us.

We can extract the values into variables using something like the
following shell script, which takes care of getting the appropriate
route from the `openshift-storage` namespace, base64-decoding the values
in the `Secret`, and replacing the `BUCKET_HOST` value:

```sh
#!/bin/sh

bucket_host=$(oc get configmap $1 -o json | jq -r .data.BUCKET_HOST)
service_name=$(cut -f1 -d. <<<$bucket_host)
service_ns=$(cut -f2 -d. <<<$bucket_host)

# get the externally visible hostname provided by the route
public_bucket_host=$(
  oc -n $service_ns get route -o json |
    jq -r  '.items[]|select(.spec.to.name=="'"$service_name"'")|.spec.host'
)

# dump configmap and secret as shell variables, replacing the
# value of BUCKET_HOST in the process.
(
  oc get configmap $1 -o json |
    jq -r '.data as $data|.data|keys[]|"\(.)=\($data[.])"'
  oc get secret $1 -o json |
    jq -r '.data as $data|.data|keys[]|"\(.)=\($data[.]|@base64d)"'
) | sed -e 's/^/export /' -e '/BUCKET_HOST/ s/=.*/='$public_bucket_host'/'
```

If we call the script `getenv.sh` and run it like this:

```sh
$ sh getenv.sh example-rgw
```

It will produce output like this:


```sh
export BUCKET_HOST="s3-openshift-storage.apps.cnv.massopen.cloud"
export BUCKET_NAME="example-noobaa-2e1bca2f-ff49-431a-99b8-d7d63a8168b0"
export BUCKET_PORT="443"
export BUCKET_REGION=""
export BUCKET_SUBREGION=""
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
```

We could accomplish something similar in Python with the following,
which shows how to use the OpenShift dynamic client to interact with
OpenShift:


```python
import argparse
import base64

import kubernetes
import openshift.dynamic


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('-n', '--namespace', required=True)
    p.add_argument('obcname')
    return p.parse_args()


args = parse_args()
k8s_client = kubernetes.config.new_client_from_config()
dyn_client = openshift.dynamic.DynamicClient(k8s_client)

v1_configmap = dyn_client.resources.get(api_version='v1', kind='ConfigMap')
v1_secret = dyn_client.resources.get(api_version='v1', kind='Secret')
v1_service = dyn_client.resources.get(api_version='v1', kind='Service')
v1_route = dyn_client.resources.get(api_version='route.openshift.io/v1', kind='Route')

configmap = v1_configmap.get(name=args.obcname, namespace=args.namespace)
secret = v1_secret.get(name=args.obcname, namespace=args.namespace)

env = dict(configmap.data)
env.update({k: base64.b64decode(v).decode() for k, v in secret.data.items()})

svc_name, svc_ns = env['BUCKET_HOST'].split('.')[:2]
routes = v1_route.get(namespace=svc_ns)
for route in routes.items:
    if route.spec.to.name == svc_name:
        break

env['BUCKET_PORT'] = 443
env['BUCKET_HOST'] = route['spec']['host']

for k, v in env.items():
    print(f'export {k}="{v}"')
```

If we run it like this:

```sh
python genenv.py -n oddbit-ocs-example example-noobaa
```

It will produce output largely identical to what we saw above with the
shell script.

If we load those variables into the environment:

```sh
$ eval $(sh getenv.sh example-rgw)
```

We can perform the same operations we executed earlier from inside the
pod:

```sh
$ aws s3 --endpoint https://$BUCKET_HOST ls
2021-02-10 14:34:12 example-rgw-425d7193-ae3a-41d9-98e3-9d07b82c9661

```
