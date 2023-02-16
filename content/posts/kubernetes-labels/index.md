---
categories: [tech]
title: "Investigating connection timeouts in a Kubernetes application"
date: "2022-09-10"
tags:
  - kubernetes
  - openshift
  - cloud
  - labels
---

We are working with an application that produces resource utilization reports for clients of our OpenShift-based cloud environments. The developers working with the application have been reporting mysterious issues concerning connection timeouts between the application and the database (a MariaDB instance). For a long time we had only high-level verbal descriptions of the problem ("I'm seeing a lot of connection timeouts!") and a variety of unsubstantiated theories (from multiple sources) about the cause. Absent a solid reproducer of the behavior in question, we looked at other aspects of our infrastructure:

- Networking seemed fine (we weren't able to find any evidence of interface errors, packet loss, or bandwidth issues)
- Storage in most of our cloud environments is provided by remote Ceph clusters. In addition to not seeing any evidence of network problems in general, we weren't able to demonstrate specific problems with our storage, either (we did spot some performance variation between our Ceph clusters that may be worth investigating in the future, but it wasn't the sort that would cause the problems we're seeing)
- My own attempts to reproduce the behavior using [mysqlslap][] did not demonstrate any problems, even though we were driving a far larger number of connections and queries/second in the benchmarks than we were in the application.

[mysqlslap]: https://dev.mysql.com/doc/refman/8.0/en/mysqlslap.html

What was going on?

I was finally able to get my hands on container images, deployment manifests, and instructions to reproduce the problem this past Friday. After working through some initial errors that weren't the errors we were looking for (insert Jedi hand gesture here), I was able to see the behavior in practice. In a section of code that makes a number of connections to the database, we were seeing:

```
Failed to create databases:

Command returned non-zero value '1': ERROR 2003 (HY000): Can't connect to MySQL server on 'mariadb' (110)

#0 /usr/share/xdmod/classes/CCR/DB/MySQLHelper.php(521): CCR\DB\MySQLHelper::staticExecuteCommand(Array)
#1 /usr/share/xdmod/classes/CCR/DB/MySQLHelper.php(332): CCR\DB\MySQLHelper::staticExecuteStatement('mariadb', '3306', 'root', 'pass', NULL, 'SELECT SCHEMA_N...')
#2 /usr/share/xdmod/classes/OpenXdmod/Shared/DatabaseHelper.php(65): CCR\DB\MySQLHelper::databaseExists('mariadb', '3306', 'root', 'pass', 'mod_logger')
#3 /usr/share/xdmod/classes/OpenXdmod/Setup/DatabaseSetupItem.php(39): OpenXdmod\Shared\DatabaseHelper::createDatabases('root', 'pass', Array, Array, Object(OpenXdmod\Setup\Console))
#4 /usr/share/xdmod/classes/OpenXdmod/Setup/DatabaseSetup.php(109): OpenXdmod\Setup\DatabaseSetupItem->createDatabases('root', 'pass', Array, Array)
#5 /usr/share/xdmod/classes/OpenXdmod/Setup/Menu.php(69): OpenXdmod\Setup\DatabaseSetup->handle()
#6 /usr/bin/xdmod-setup(37): OpenXdmod\Setup\Menu->display()
#7 /usr/bin/xdmod-setup(22): main()
#8 {main}
```

Where `110` is `ETIMEDOUT`, "Connection timed out".

The application consists of two [Deployment][] resources, one that manages a MariaDB pod and another that manages the application itself. There are also the usual suspects, such as [PersistentVolumeClaims][pvc] for the database backing store, etc, and a [Service][] to allow the application to access the database.

[deployment]: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
[pvc]: https://kubernetes.io/docs/concepts/storage/persistent-volumes/
[service]: https://kubernetes.io/docs/concepts/services-networking/service/

While looking at this problem, I attempted to look at the logs for the application by running:

```
kubectl logs deploy/moc-xdmod
```

But to my surprise, I found myself looking at the logs for the MariaDB container instead...which provided me just about all the information I needed about the problem.

## How do Deployments work?

To understand what's going on, let's first take a closer look at a Deployment manifest.  The basic framework is something like this:

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example
spec:
  selector:
    matchLabels:
      app: example
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: example
    spec:
      containers:
        - name: example
          image: docker.io/alpine:latest
          command:
            - sleep
            - inf
```

There are labels in three places in this manifest:

1. The Deployment itself has labels in the `metadata` section.
2. There are labels in `spec.template.metadata` that will be applied to Pods spawned by the Deployment.
3. There are labels in `spec.selector` which, in the words of [the documentation]:

      > defines how the Deployment finds which Pods to manage

It's not spelled out explicitly anywhere, but the `spec.selector` field is also used to identify to which pods to attach when using the Deployment name in a command like `kubectl logs`: that is, given the above manifest, running `kubectl logs deploy/example` would look for pods that have label `app` set to `example`.

With this in mind, let's take a look at how our application manifests are being deployed. Like most of our applications, this is deployed using [Kustomize][]. The `kustomization.yaml` file for the application manifests looked like this:

[kustomize]: https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/

```
commonLabels:
  app: xdmod

resources:
  - svc-mariadb.yaml
  - deployment-mariadb.yaml
  - deployment-xdmod.yaml
```

That `commonLabels` statement will apply the label `app: xdmod` to all of the resources managed by the `kustomization.yaml` file. The Deployments looked like this:

For MariaDB:

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mariadb
spec:
  selector:
    matchLabels:
      app: mariadb
  template:
    metadata:
      labels:
        app: mariadb
```

For the application experience connection problems:

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: moc-xdmod
spec:
  selector:
    matchLabels:
      app: xdmod
  template:
    metadata:
      labels:
        app: xdmod
```

The problem here is that when these are processed by `kustomize`, the `app` label hardcoded in the manifests will be replaced by the `app` label defined in the `commonLabels` section of `kustomization.yaml`. When we run `kustomize build` on these manifests, we will have as output:

```
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: xdmod
  name: mariadb
spec:
  selector:
    matchLabels:
      app: xdmod
  template:
    metadata:
      labels:
        app: xdmod
---
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: xdmod
  name: moc-xdmod
spec:
  selector:
    matchLabels:
      app: xdmod
  template:
    metadata:
      labels:
        app: xdmod
```

In other words, all of our pods will have the same labels (because the `spec.template.metadata.labels` section is identical in both Deployments). When I run `kubectl logs deploy/moc-xdmod`, I'm just getting whatever the first match is for a query that is effectively the same as `kubectl get pod -l app=xdmod`.

So, that's what was going on with the `kubectl logs` command.

## How do services work?

A Service manifest in Kubernetes looks something like this:

```
apiVersion: v1
kind: Service
metadata:
  name: mariadb
spec:
  selector:
    app: mariadb
  ports:
    - protocol: TCP
      port: 3306
      targetPort: 3306
```

Here, `spec.selector` has a function very similar to what it had in a `Deployment`: it selects pods to which the Service will direct traffic. From [the documentation][service], we know that a Service proxy will select a backend either in a round-robin fashion (using the legacy user-space proxy) or in a random fashion (using the iptables proxy) (there is also an [IPVS][] proxy mode, but that's not available in our environment).

[ipvs]: http://www.linuxvirtualserver.org/software/ipvs.html

Given what we know from the previous section about Deployments, you can probably see what's going on here:

1. There are multiple pods with identical labels that are providing distinct services
1. For each incoming connection, the service proxy selects a Pod based on the labels in the service's `spec.selector`.
1. With only two pods involved, there's a 50% chance that traffic targeting our MariaDB instance will in fact be directed to the application pod, which will simply drop the traffic (because it's not listening on the appropriate port).

We can see the impact of this behavior by running a simple loop that attempts to connect to MariaDB and run a query:

```
while :; do
  _start=$SECONDS
  echo -n "$(date +%T) "
  timeout 10 mysql -h mariadb -uroot -ppass -e 'select 1' > /dev/null && echo -n OKAY || echo -n FAILED
  echo " $(( SECONDS - _start))"
  sleep 1
done
```

Which outputs:

```
01:41:30 OKAY 1
01:41:32 OKAY 0
01:41:33 OKAY 1
01:41:35 OKAY 0
01:41:36 OKAY 3
01:41:40 OKAY 1
01:41:42 OKAY 0
01:41:43 OKAY 3
01:41:47 OKAY 3
01:41:51 OKAY 4
01:41:56 OKAY 1
01:41:58 OKAY 1
01:42:00 FAILED 10
01:42:10 OKAY 0
01:42:11 OKAY 0
```

Here we can see that connection time is highly variable, and we occasionally hit the 10 second timeout imposed by the `timeout` call.

## Solving the problem

In order to resolve this behavior, we want to ensure (a) that Pods managed by a Deployment are uniquely identified by their labels and that (b) `spec.selector` for both Deployments and Services will only select the appropriate Pods. We can do this with a few simple changes.

It's useful to apply some labels consistently across all of the resource we generate, so we'll keep the existing `commonLabels` section of our `kustomization.yaml`:

```
commonLabels:
  app: xdmod
```

But then in each Deployment we'll add a `component` label identifying the specific service, like this:

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mariadb
  labels:
    component: mariadb
spec:
  selector:
    matchLabels:
      component: mariadb
  template:
    metadata:
      labels:
        component: mariadb
```

When we generate the final manifest with `kustomize`, we end up with:

```
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: xdmod
    component: mariadb
  name: mariadb
spec:
  selector:
    matchLabels:
      app: xdmod
      component: mariadb
  template:
    metadata:
      labels:
        app: xdmod
        component: mariadb
```

In the above output, you can see that `kustomize` has combined the `commonLabel` definition with the labels configured individually in the manifests. With this change, `spec.selector` will now select only the pod in which MariaDB is running.

We'll similarly modify the Service manifest to look like:

```
apiVersion: v1
kind: Service
metadata:
  name: mariadb
spec:
  selector:
    component: mariadb
  ports:
    - protocol: TCP
      port: 3306
      targetPort: 3306
```

Resulting in a generated manifest that looks like:

```
apiVersion: v1
kind: Service
metadata:
  labels:
    app: xdmod
  name: mariadb
spec:
  ports:
  - port: 3306
    protocol: TCP
    targetPort: 3306
  selector:
    app: xdmod
    component: mariadb
```

Which, as with the Deployment, will now select only the correct pods.

With these changes in place, if we re-run the test loop I presented earlier, we see as output:

```
01:57:27 OKAY 0
01:57:28 OKAY 0
01:57:29 OKAY 0
01:57:30 OKAY 0
01:57:31 OKAY 0
01:57:32 OKAY 0
01:57:33 OKAY 0
01:57:34 OKAY 0
01:57:35 OKAY 0
01:57:36 OKAY 0
01:57:37 OKAY 0
01:57:38 OKAY 0
01:57:39 OKAY 0
01:57:40 OKAY 0
```

There is no variability in connection time, and there are no timeouts.
