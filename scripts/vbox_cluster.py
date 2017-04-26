#!/usr/bin/env python

import os
import sys
import time
import logging
import argparse
import requests
import subprocess
import urllib.parse


log = logging.getLogger('main')
tmp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tmp')
ipxe_iso = os.path.join(tmp_dir, 'ipxe.iso')

if sys.platform == 'darwin':
    vbox_tftp_dir = os.path.expanduser('~/Library/VirtualBox/TFTP')
else:
    vbox_tftp_dir = os.path.expanduser('~/.VirtualBox/TFTP')


def main():
    args = parse_args()
    logging.basicConfig(level='NOTSET')

    seedbox_url = args.seedbox_url
    if not seedbox_url:
        seedbox_ip = get_hostonlyif_ipaddress(args.host_only_network)
        if not seedbox_ip:
            raise Exception("Can't get host-only network IP", args.host_only_network)
        seedbox_url = 'http://{}:5000/'.format(seedbox_ip)

    ipxe_script_name = args.cluster_name + '.ipxe'
    prepare_vbox_ipxe(ipxe_script_name, seedbox_url)

    instance_names = [format_instance_name(args.cluster_name, idx + 1) for idx in range(args.num_instances)]

    if args.delete:
        wait = False
        for instance_name in instance_names:
            log.info('Powering off VM %s', instance_name)
            poweroff_cmd = subprocess.run(['VBoxManage', 'controlvm',
                                           instance_name,
                                           'poweroff'])
            if poweroff_cmd.returncode == 0:
                wait = True  # VirtualBox doesn't release a lock for some time after poweroff

        if wait:
            time.sleep(10)

        for instance_name in instance_names:
            log.info('Deleting VM %s', instance_name)
            subprocess.run(['VBoxManage', 'unregistervm',
                            instance_name,
                            '--delete'])

    for instance_name in instance_names:
        log.info('Creating VM %s', instance_name)
        subprocess.run(['VBoxManage', 'createvm',
                        '--name', instance_name,
                        '--groups', '/' + args.cluster_name,
                        '--ostype', 'Linux26_64',
                        '--register'],
                       check=True)

        log.info('Configuring VM %s', instance_name)
        subprocess.run(['VBoxManage', 'modifyvm',
                        instance_name,
                        '--memory', str(args.memory),
                        '--nic1', 'nat',
                        '--nattftpfile1', ipxe_script_name,
                        '--nic2', 'hostonly',
                        '--hostonlyadapter2', args.host_only_network],
                       check=True)

        config_path = get_vm_config_file_path(instance_name)
        if not config_path:
            raise Exception("Can't get VM config path", instance_name)

        base_path = os.path.dirname(config_path)
        disk_path = os.path.join(base_path, 'ide1.vdi')

        log.info('Creating a disk for VM %s', instance_name)
        subprocess.run(['VBoxManage', 'createhd',
                        '--filename', disk_path,
                        '--size', str(args.disk_size)],
                       check=True)

        storage_controller_name = 'IDE Controller'

        log.info('Attaching IDE controller to VM %s', instance_name)
        subprocess.run(['VBoxManage', 'storagectl',
                        instance_name,
                        '--name', storage_controller_name,
                        '--add', 'ide',
                        '--controller', 'PIIX4'],
                       check=True)

        log.info('Attaching disk to VM %s', instance_name)
        subprocess.run(['VBoxManage', 'storageattach',
                        instance_name,
                        '--storagectl', storage_controller_name,
                        '--port', '0',
                        '--device', '0',
                        '--type', 'hdd',
                        '--medium', disk_path],
                       check=True)

        log.info('Attaching ipxe.iso to VM %s', instance_name)
        subprocess.run(['VBoxManage', 'storageattach',
                        instance_name,
                        '--storagectl', storage_controller_name,
                        '--port', '0',
                        '--device', '1',
                        '--type', 'dvddrive',
                        '--medium', ipxe_iso],
                       check=True)

    if args.start:
        for instance_name in instance_names:
            log.info('Starting VM %s', instance_name)
            subprocess.run(['VBoxManage', 'startvm',
                            instance_name,
                            '--type', 'headless'],
                           check=True)


def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('cluster_name',
                            help='cluster name')
    arg_parser.add_argument('num_instances', type=int,
                            help='number of instances to create')
    arg_parser.add_argument('-d', '--delete', action='store_true', default=False,
                            help='delete all VMs first')
    arg_parser.add_argument('--memory', type=int, default=1024,
                            help='amount of RAM on an instance')
    arg_parser.add_argument('--disk-size', type=int, default=262144,
                            help='instance disk size in megabytes')
    arg_parser.add_argument('--start', action='store_true', default=False,
                            help='start instances after creation')
    arg_parser.add_argument('--host-only-network', default='vboxnet0',
                            help='VirtualBox host-only network name')
    arg_parser.add_argument('--seedbox-url',
                            help='URL of your seedbox installation (defaults to first IP of host-only network)')
    return arg_parser.parse_args()


def format_instance_name(cluster_name, idx):
    return '{}-node{:02}'.format(cluster_name, idx)


def prepare_vbox_ipxe(ipxe_script_name, seedbox_url):
    try:
        os.mkdir(vbox_tftp_dir)
    except FileExistsError:
        pass

    ipxe_script_path = os.path.join(vbox_tftp_dir, ipxe_script_name)
    ipxe_script = '#!ipxe\ndhcp net1\nchain {}\n'.format(urllib.parse.urljoin(seedbox_url, 'ipxe'))
    with open(ipxe_script_path, 'w') as f:
        f.write(ipxe_script)

    if not os.path.exists(ipxe_iso):
        os.makedirs(tmp_dir, exist_ok=True)
        log.info('Downloading ipxe.iso')
        source_url = 'http://boot.ipxe.org/ipxe.iso'
        resp = requests.get(source_url, stream=True)
        resp.raise_for_status()
        with open(ipxe_iso, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=1024):
                f.write(chunk)


def get_vm_config_file_path(vm_name):
    stdout = subprocess.run(['VBoxManage', 'showvminfo', vm_name], check=True, stdout=subprocess.PIPE).stdout
    for line in stdout.splitlines():
        parts = line.split(b':', maxsplit=1)
        if len(parts) == 2 and parts[0] == b'Config file':
            return os.fsdecode(parts[1].strip())


def get_hostonlyif_ipaddress(ifname):
    stdout = subprocess.run(['VBoxManage', 'list', 'hostonlyifs'], check=True, stdout=subprocess.PIPE).stdout

    current_if = None
    for line in stdout.splitlines():
        if not line:
            current_if = None
        else:
            parts = line.split(b':', maxsplit=1)
            key = parts[0]
            value = parts[1].strip()
            if key == b'Name':
                current_if = value.decode()
            elif current_if == ifname:
                if key == b'IPAddress':
                    return value.decode()


if __name__ == '__main__':
    main()
