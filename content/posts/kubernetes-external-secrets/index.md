---
categories:
- tech
date: '2021-09-03'
tags:
- openshift
- kubernetes
- secrets
title: 'Kubernetes External Secrets'

---

At *$JOB* we maintain the configuration for our OpenShift clusters in a public git repository. Changes in the git repository are applied automatically using [ArgoCD][] and [Kustomize][]. This works great, but the public nature of the repository means we need to find a secure solution for managing secrets (such as passwords and other credentials necessary for authenticating to external services). In particular, we need a solution that permits our public repository to be the source of truth for our cluster configuration, without compromising our credentials.

[argocd]: https://argo-cd.readthedocs.io/en/stable/
[kustomize]: https://kustomize.io/

## Rejected options

We initially looked at including secrets directly in the repository through the use of the [KSOPS][] plugin for Kustomize, which uses [sops][] to encrypt secrets with GPG keys. There are some advantages to this arrangement:

[ksops]: https://github.com/viaduct-ai/kustomize-sops
[sops]: https://github.com/mozilla/sops

- It doesn't require any backend service
- It's easy to control read access to secrets in the repository by encrypting them to different recipients.

There were some minor disadvantages:

- We can't install ArgoCD via the operator because we need a customized image that includes KSOPS, so we have to maintain our own ArgoCD image.

And there was one major problem:

- Using GPG-encrypted secrets in a git repository makes it effectively impossible to recover from a key compromise.

One a private key is compromised, anyone with access to that key and the git repository will be able to decrypt data in historical commits, even if we re-encrypt all the data with a new key.

Because of these security implications we decided we would need a different solution (it's worth noting here that Bitnami [Sealed Secrets][] suffers from effectively the same problem).

[sealed secrets]: https://github.com/bitnami-labs/sealed-secrets

## Our current solution

We've selected a solution that uses the [External Secrets][] project in concert with the AWS [SecretsManager] service.

[secretsmanager]: https://aws.amazon.com/secrets-manager/
[external secrets]: https://github.com/external-secrets/kubernetes-external-secrets

### Kubernetes external secrets

The [External Secrets][] project allows one to store secrets in an external secrets store, such as AWS [SecretsManager][], Hashicorp [Vault][], and others [^1]. The manifests that get pushed into your OpenShift cluster contain only pointers (called `ExternalSecrets`) to those secrets; the external secrets controller running on the cluster uses the information contained in the `ExternalSecret` in combination with stored credentials to fetch the secret from your chosen backend and realize the actual `Secret` resource. An external secret manifest referring to a secret named `mysceret` stored in AWS SecretsManager would look something like:

[vault]: https://www.vaultproject.io/
[^1]: E.g. Azure Key Vault, Google Secret Manager, Alibaba Cloud KMS Secret Manager, Akeyless

```
apiVersion: "kubernetes-client.io/v1"
kind: ExternalSecret
metadata:
  name: example-secret
spec:
  backendType: secretsManager
  data:
    - key: mysecret
      name: mysecretvalue
```

This model means that no encrypted data is ever stored in the git repository, which resolves the main problem we had with the solutions mentioned earlier.

External Secrets can be installed into your Kubernetes environment using Helm, or you can use `helm template` to generate manifests locally and apply them using Kustomize or some other tool (this is the route we took).

### AWS SecretsManager Service

AWS [SecretsManager][] is a service for storing and managing secrets and making them accessible via an API. Using SecretsManager we have very granular control over who can view or modify secrets; this allows us, for example, to create cluster-specific secret readers that can only read secrets intended for a specific cluster (e.g. preventing our development environment from accidentally using production secrets).

SecretsManager provides automatic versioning of secrets to prevent loss of data if you inadvertently change a secret while still requiring the old value.

We can create secrets through the AWS SecretsManager console, or we can use the [AWS CLI][], which looks something like:

```
aws secretsmanager create-secret \
  --name mysecretname \
  --secret-string mysecretvalue
```

[aws cli]: https://aws.amazon.com/cli/

### Two great tastes that taste great together

This combination solves a number of our problems:

- Because we're not storing actual secrets in the repository, we don't need to worry about encrypting anything.

- Because we're not managing encrypted data, replacing secrets is much easier.

- There's a robust mechanism for controlling access to secrets.

- This solution offers a separation of concern that simply wasn't possible with the KSOPS model: someone can maintain secrets without having to know anything about Kubernetes manifests, and someone can work on the repository without needing to know any secrets.

## Creating external secrets

In its simplest form, an `ExternalSecret` resource maps values from specific named secrets in the backend to keys in a `Secret` resource. For example, if we wanted to create a `Secret` in OpenShift with the username and password for an external service, we could create to separate secrets in SecretsManager. One for the username:

```
aws secretsmanager create-secret \
  --name cluster/cluster1/example-secret-username \
  --secret-string foo
```

And one for the password:

```
aws secretsmanager create-secret \
  --name cluster/cluster1/example-secret-password \
  --secret-string bar \
  --tags Key=cluster,Value=cluster1
```

And then create an `ExternalSecret` manifest like this:

```
apiVersion: "kubernetes-client.io/v1"
kind: ExternalSecret
metadata:
  name: example-secret
spec:
  backendType: secretsManager
  data:
    - key: cluster/cluster1/example-secret-username
      name: username
    - key: cluster/cluster1/example-secret-password
      name: password
```

This instructs the External Secrets controller to create an `Opaque` secret named `example-secret` from data in AWS SecretsManager. The value of the `username` key will come from the secret named `cluster/cluster1/example-secret-username`, and similarly for `password`. The resulting `Secret` resource will look something like this:

```
apiVersion: v1
kind: Secret
metadata:
  name: example-secret
type: Opaque
data:
  password: YmFy
  username: Zm9v
```

### Templates for structured data

In the previous example, we created two separate secrets in SecretsManager for storing a username and password. It might be more convenient if we could store both credentials in a single secret. Thanks to the [templating][] support in External Secrets, we can do that!

[templating]: https://github.com/external-secrets/kubernetes-external-secrets#templating

Let's redo the previous example, but instead of using two separate secrets, we'll create a single secret named `cluster/cluster1/example-secret` in which the secret value is a JSON document containing both the username and password:

```
aws secretsmanager create-secret \
  --name cluster/cluster1/example-secret \
  --secret-string '{"username": "foo", "password": "bar"}'
```

NB: The [jo][] utility is a neat little utility for generating JSON from the command line; using that we could write the above like this...

[jo]: https://github.com/jpmens/jo

```
aws secretsmanager create-secret \
  --name cluster/cluster1/example-secret \
  --secret-string $(jo username=foo password=bar)
```

...which makes it easier to write JSON without missing a quote, closing bracket, etc.

We can extract these values into the appropriate keys by adding a `template` section to our `ExternalSecret`, and using the `JSON.parse` template function, like this:

```
apiVersion: "kubernetes-client.io/v1"
kind: ExternalSecret
metadata:
  name: example-secret
  namespace: sandbox
spec:
  backendType: secretsManager
  data:
    - key: cluster/cluster1/example-secret
      name: creds
  template:
    stringData:
      username: "<%= JSON.parse(data.creds).username %>"
      password: "<%= JSON.parse(data.creds).password %>"
```

The result secret will look like:

```
apiVersion: v1
kind: Secret
metadata:
  name: example-secret
type: Opaque
data:
  creds: eyJ1c2VybmFtZSI6ICJmb28iLCAicGFzc3dvcmQiOiAiYmFyIn0=
  password: YmFy
  username: Zm9v
```

Notice that in addition to the values created in the `template` section, the `Secret` also contains any keys defined in the `data` section of the `ExternalSecret`.

Templating can also be used to override the secret type if you want something other than `Opaque`, add metadata, and otherwise influence the generated `Secret`.

<!-- vim: set tw=0 linebreak : -->
