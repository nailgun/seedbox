# seedbox

Baremetal CoreOS cluster provisioner with web UI. Currently it's primary goal is to boot CoreOS
clusters using PXE without installation. But it easily can be extended for any provision method.

## What is wrong with CoreOS matchbox

Actually it's based on ignition config files from [CoreOS matchbox](https://github.com/coreos/matchbox).
But ignition config in seedbox are splet into mutiple files to increase readability. This is also
provides the most important difference: you can reuse parts of configuration in different setups.
Actually using seedbox you just set checkboxes for which features you need on a cluster and nodes. And
config renderer will generate ignition config file for you. Systemd unit files are grouped together
with required files to help track dependencies. In matchbox some units described at beginning of an
ignition file require files described at end of the file. This is hard to read and maintain.

Reading matchbox example ignition files you can see many duplications. K8s controller and worker have
many common stuff. With seedbox you get flexibility to have some nodes just etcd servers, some k8s
controllers and workers without maintaining a bunch of long ignition files.

## Web UI

![](docs/img/cluster-create.png)

![](docs/img/node-create.png)

![](docs/img/node-list.png)

![](docs/img/user-list.png)

## PKI

You will have out of a box PKI. It's simple but powerful enough to have one CA per cluster. It will
automatically issue certificates for nodes and users. It will also will warn you if there is something
wrong with certificates (expired, changed name, etc).

Credentials are automatically transferred to nodes in most secure manner which is possible in automatic
provision.

## Node state tracking

Node notifies seedbox after successful boot and uploads active ignition config so seedbox can track
current state of a cluster.

## Ignition file compare

If you afraid to launch clusters with new untested software you can use provided `ignition-compare`
script to compare rendered configuration with yours. Copy your ignition config from a server (it is stored
in `/run/ignition.json`). Next start to provision using seedbox. All nodes will report applied ignition
config back to seedbox and you can download it from web UI. Next run
`python ignition-compare.py your.json seedbox.json | colordiff | less` and see differences.

Seedbox was developed by constantly checking differences with matchbox'es `k8s-controller` and `k8s-worker`
example profiles. And changes are minimal.

## Roadmap

* add k8s apiserver loadbalancers provision
* add [k8s authorization webhook](https://kubernetes.io/docs/admin/authorization/)
* add support for persistent CoreOS installation
* add support for bootkube
