def get_kernel_arguments(node):
    args = ['coreos.first_boot=yes']

    if node.coreos_autologin:
        args.append('coreos.autologin')

    for console in node.linux_consoles.split(','):
        args.append('console='+console)

    args.append('root=' + node.root_partition)

    if node.disable_ipv6:
        args.append('ipv6.disable=1')

    return args
