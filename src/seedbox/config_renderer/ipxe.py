response_template = """#!ipxe
set base-url {images_base_url}
kernel ${{base-url}}coreos_production_pxe.vmlinuz {kernel_args}
initrd ${{base-url}}coreos_production_pxe_image.cpio.gz
boot
"""


def render(node, url_root):
    kernel_args = get_kernel_arguments(node, url_root)
    return response_template.format(images_base_url=node.cluster.boot_images_base_url,
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

    if not node.maintenance_mode:
        args.append('root=' + node.root_partition)

    if node.disable_ipv6:
        args.append('ipv6.disable=1')

    if node.debug_boot:
        args += [
            'systemd.journald.forward_to_kmsg=1',
            'systemd.journald.max_level_kmsg=debug',   # requires systemd-232
        ]

    return args
