---
categories: [tech]
title: Applying custom configuration to Nginx Gateway Fabric
date: "2023-11-17"
tags:
  - kubernetes
  - nginx
  - gateway-api
  - containers
---

In this post, we take a look at how to apply custom Nginx configuration directives when you're using the [NGINX Gateway Fabric].

[nginx gateway fabric]: https://github.com/nginxinc/nginx-gateway-fabric

## What's the NGINX Gateway Fabric?

The NGINX Gateway Fabric is an implementation of the Kubernetes [Gateway API].

[gateway api]: https://gateway-api.sigs.k8s.io/

## What's the Gateway API?

The Gateway API is an evolution of the [Ingress] API; it aims to provide a flexible mechanism for managing north/south network traffic (that is, traffic entering or exiting your Kubernetes cluster), with additional work to support east/west traffic (traffic between pods in your cluster).

[ingress]: https://kubernetes.io/docs/concepts/services-networking/ingress/

## What's this about custom configuration?

I've deployed a local development cluster, and I wanted to be able to push images into an image registry hosted on the cluster. This requires (a) running a registry, which is easy, and (b) somehow exposing that registry outside the cluster, which is also easy unless you decide to make it more complex.

In this case, I decided that rather than running an Ingress provider I was going to start familiarizing myself with the Gateway API, so I deployed NGINX Gateway Fabric. My first attempt at pushing an image into the registry looked like this:

```
$ podman push --tls-verify=false example registry.apps.cluster1.house/example:latest
Getting image source signatures
Copying blob b9fe5313d237 done   |
Copying blob cc2447e1835a done   |
Copying blob cb8b0886acfb done   |
Copying blob c4219a5645ea [===>----------------------------------] 9.3MiB / 80.2MiB | 372.7 MiB/s
Copying blob c6e5c62d1726 done   |
Copying blob 9ee7eb11f876 done   |
Copying blob f064c46326cb done   |
Copying blob 9c45ffa2a02a done   |
Copying blob 9a6c9897f309 done   |
Copying blob 27a0dbb2828e done   |
Error: writing blob: uploading layer chunked: StatusCode: 413, <html>
<head><title>413 Request Entity Too Large<...
```

Nginx, by default, restricts the maximum size of a request body to `1m`, which is to say, 1 megabyte. You can increase (or remove) this limit by setting the [`client_max_body_size`][client_max_body_size] parameter...but how do you do this in the context of a managed deployment like the NGINX Gateway Fabric?

[client_max_body_size]: https://nginx.org/en/docs/http/ngx_http_core_module.html#client_max_body_size

## Via the API?

As of this writing, there is no mechanism to apply custom configuration options via the API (although there is ongoing work to provide this, see issue [#1258]).

[#1258]: https://github.com/nginxinc/nginx-gateway-fabric/issues/1258

## What about dropping a config file into conf.d?

My first thought was that I could mount a custom configuration file into `/etc/nginx/conf.d`, along the lines of:


```
...
containers:
  - name: nginx
    volumeMounts:
      - name: nginx-extra-conf
        mountPath: /etc/nginx/conf.d/client_max_body_size.conf
        subPath: client_max_body_size
...
volumes:
  - name: nginx-extra-conf
    configMap:
      name: nginx-extra-conf
```

...but this fails because the Nginx controller [explicitly cleans out that directory on startup][cleanup] and is unhappy if it is unable to delete a file.

[cleanup]: https://github.com/nginxinc/nginx-gateway-fabric/blob/7de105c7dd09ccfca5823d6941ac12c520257221/internal/mode/static/manager.go#L123-L129

## Replacing nginx.conf

Right now, the solution is to replace `/etc/nginx/nginx.conf`. This is a relatively simple operation using [kustomize] to apply a patch to the deployment manifests.

[kustomize]: https://kustomize.io

### Grab the original configuration

First, we need to retrieve the *original* `nginx.conf`:

```
mkdir configs
podman run --rm --entrypoint cat \
  ghcr.io/nginxinc/nginx-gateway-fabric/nginx:1.0.0 /etc/nginx/nginx.conf > configs/nginx.conf
```

Modify `configs/nginx.conf` as necessary; in my case, I added the following line to the `http` section:

```
client_max_body_size 0;
```

### Patch the deployment

We can deploy the stock NGINX Gateway Fabric with a `kustomization.yaml` file like this:

```
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
commonLabels:
  nginxGatewayVersion: v1.0.0

resources:
- https://github.com/nginxinc/nginx-gateway-fabric/releases/download/v1.0.0/crds.yaml
- https://github.com/nginxinc/nginx-gateway-fabric/releases/download/v1.0.0/nginx-gateway.yaml
- https://raw.githubusercontent.com/nginxinc/nginx-gateway-fabric/v1.0.0/deploy/manifests/service/nodeport.yaml
```

To patch the Deployment resource, we extend the `kustomization.yaml` with the following patch:

```
patches:
  - patch: |
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: nginx-gateway
        namespace: nginx-gateway
      spec:
        template:
          spec:
            containers:
              - name: nginx
                volumeMounts:
                  - mountPath: /etc/nginx/nginx.conf
                    name: nginx-conf-override
                    subPath: nginx.conf
            volumes:
              - name: nginx-conf-override
                configMap:
                  name: nginx-conf-override
```

And then we add a `confdigMapGenerator` to generate the `nginx-conf-override` ConfigMap:

```
configMapGenerator:
  - name: nginx-conf-override
    namespace: nginx-gateway
    options:
      disableNameSuffixHash: true
    files:
      - configs/nginx.conf
```

Now when we deploy from this directory...

```
kubectl apply -k . --server-side
```

...the deployment includes our patched `nginx.conf` and we are able to successfully push images into the cluster registry.

---

I've included the complete [`kustomization.yaml`](kustomization.yaml) alongside this post.
