---
categories:
- tech
date: '2020-09-27'
filename: 2020-09-27-installing-metallb-on-openshif.md
tags:
- openshift
- kustomize
- metallb
title: Installing metallb on OpenShift with Kustomize

---

Out of the box, OpenShift (4.x) on bare metal doesn't come with any
integrated load balancer support (when installed in a cloud environment,
OpenShift typically makes use of the load balancing features available from
the cloud provider). Fortunately, there are third party solutions available
that are designed to work in bare metal environments. [MetalLB][] is a
popular choice, but requires some minor fiddling to get it to run properly
on OpenShift.

If you read through the [installation instructions][], you will see [this
note][] about installation on OpenShift:

> To run MetalLB on Openshift, two changes are required: changing the pod
> UIDs, and granting MetalLB additional networking privileges.
> 
> Pods get UIDs automatically assigned based on an OpenShift-managed UID
> range, so you have to remove the hardcoded unprivileged UID from the
> MetalLB manifests. You can do this by removing the
> spec.template.spec.securityContext.runAsUser field from both the
> controller Deployment and the speaker DaemonSet.
> 
> Additionally, you have to grant the speaker DaemonSet elevated
> privileges, so that it can do the raw networking required to make
> LoadBalancers work. You can do this with:

The docs here suggest some manual changes you can make, but it's possible
to get everything installed correctly using [Kustomize][] (which makes
sense especially given that the MetalLB docs already include instructions
[on using Kustomize][]).

A vanilla installation of MetalLB with Kustomize uses a `kustomization.yml`
file that looks like this:

```
namespace: metallb-system

resources:
  - github.com/metallb/metallb//manifests?ref=v0.9.3
  - configmap.yml
  - secret.yml
```

(Where `configmap.yml` and `secret.yml` are files you create locally
containing, respectively, the MetalLB configuration and a secret used to
authenticate cluster members.)

## Fixing the security context

In order to remove the `runAsUser` directive form the template
`securityContext` setting, we can use the [patchesStrategicMerge][]
feature. In our `kustomization.yml` file we add:

```
patches:
  - |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: controller
        namespace: metallb-system
      spec:
        template:
          spec:
            securityContext:
              $patch: replace
              runAsNonRoot: true
```

This instructs `kustomize` to replace the contents of the `securityContext`
key with the value included in the patch (without the `$patch: replace`
directive, the default behavior is to merge the contents, which in this
situation would effectively be a no-op).

We can accomplish the same thing using [jsonpatch][] syntax. In this case,
we would write:

```
patches:
  - target:
      kind: Deployment
      name: controller
      namespace: metallb-system
    patch: |-
      - op: remove
        path: /spec/template/spec/securityContext/runAsUser
```

With either solution, the final output includes a `securityContext` setting
that looks like this:

```
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
```

## Granting elevated privileges

The MetaLB docs suggest running:

```
oc adm policy add-scc-to-user privileged -n metallb-system -z speaker
```

But we can configure the same privilege level by setting up an appropriate
role binding as part of our Kustomize manifests.

First, we create an `allow-privileged` cluster role by adding the following
manifest in `clusterrole.yml`:

```
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: allow-privileged
rules:
  - apiGroups:
      - security.openshift.io
    resourceNames:
      - privileged
    resources:
      - securitycontextconstraints
    verbs:
      - use
```

Then we bind the `speaker` service account to the `allow-privileged` role
by adding a `ClusterRoleBinding` in `rolebinding.yml`:

```
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: metallb-allow-privileged
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: allow-privileged
subjects:
  - kind: ServiceAccount
    name: speaker
    namespace: metallb-system
```

You will need to add these new manifests to your `kustomization.yml`, which
should now look like:

```
namespace: metallb-system

resources:
  - github.com/metallb/metallb//manifests?ref=v0.9.3
  - configmap.yml
  - secret.yml
  - clusterole.yml
  - rolebinding.yml

patches:
  - target:
      kind: Deployment
      name: controller
      namespace: metallb-system
    patch: |-
      - op: remove
        path: /spec/template/spec/securityContext/runAsUser
```

## Conclusion

The changes described here will result in a successful MetalLB deployment
into your OpenShift environment.

[installation instructions]: https://metallb.universe.tf/installation/
[this note]: https://metallb.universe.tf/installation/clouds/#metallb-on-openshift-ocp
[metallb]: https://metallb.universe.tf/
[kustomize]: https://github.com/kubernetes-sigs/kustomize
[on using kustomize]: https://metallb.universe.tf/installation/#installation-with-kustomize
[patchesStrategicMerge]: https://kubectl.docs.kubernetes.io/pages/reference/kustomize.html#patchesstrategicmerge
[jsonpatch]: https://tools.ietf.org/html/rfc6902
