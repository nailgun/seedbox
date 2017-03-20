response_template = """#!ipxe
set base-url /image/{coreos_channel}/{coreos_version}
kernel ${{base-url}}/coreos_production_pxe.vmlinuz {kernel_args}
initrd ${{base-url}}/coreos_production_pxe_image.cpio.gz
boot
"""


def render(node, url_root):
    kernel_args = get_kernel_arguments(node, url_root)
    return response_template.format(coreos_channel=node.coreos_channel,
                                    coreos_version=node.coreos_version,
                                    kernel_args=' '.join(kernel_args))


def get_kernel_arguments(node, url_root):
    args = [
        'coreos.config.url={}ignition'.format(url_root),
        'coreos.first_boot=yes',
    ]

    if node.coreos_autologin:
        args.append('coreos.autologin')

    for console in node.linux_consoles.split(','):
        args.append('console=' + console)

    # TODO: if enabled, won't boot with wiped partition table
    # TODO: if disabled, root will be in tmpfs and will eat RAM
    # args.append('root=' + node.root_partition)

    if node.disable_ipv6:
        args.append('ipv6.disable=1')

    return args
