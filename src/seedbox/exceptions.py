class K8sNoClusterApiserver(Exception):
    def __str__(self):
        return "No node with k8s apiserver"


class NoRootPartition(Exception):
    def __str__(self):
        return "No partition labeled ROOT defined"


class MultipleRootPartitions(Exception):
    def __str__(self):
        return "More than one partition labeled ROOT defined"


class MultiplePersistentMountpoints(Exception):
    def __str__(self):
        return "More than one persistent mountpoint defined"
