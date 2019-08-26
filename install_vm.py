#!/usr/bin/python3
'''
virt-install -c 'qemu+ssh://ctld@10.99.1.3/system' --noautoconsole --autostart --name="chin-chen-test2" --os-type=linux --os-variant=ubuntu16.04 --vcpu=2 --cpu=Broadwell-noTSX-IBRS --memory=2048 --disk=pool=default,size=20,sparse=no --network=bridge=br-internal --network=bridge=br-external --boot=network,hd

maas ctld machine update $SYSTEM_ID hostname=$HOSTNAME power_type=virsh power_parameters_power_address=qemu+ssh://ubuntu@$KVM_HOST/system power_parameters_power_id=$HOSTNAME
maas ctld machine update s7mq3h hostname=onsite-exam power_type=virsh power_parameters_power_address=qemu+ssh://ctld@10.99.1.3/system power_parameters_power_id=onsite-exam

maas $PROFILE machine commission $SYSTEM_ID
maas ctld machine commission s7mq3h
'''
import argparse
import subprocess
import re
import json
import datetime

RED = '\033[31m'
END = '\033[0m'

def create_parser():
    # Create the parser and add arguments to it. 
    parser = argparse.ArgumentParser(description='Automatically install a new VM')
    parser.add_argument('name', type=str, help='vm name')
    parser.add_argument('--host', dest='host_ip', help='IP address of the host which you are installing the VM on.', type=str, default='10.99.1.3')
    parser.add_argument('--username', dest='username', help='Username of the host which you are install the VM on.', type=str, default='ctld')
    parser.add_argument('--ram', dest='ram', help='Size of RAM of the new VM', type=int, default=2048)
    parser.add_argument('--core', dest='core', help='Number of CPU core of the new VM', type=int, default=2)
    parser.add_argument('--storage', dest='storage', help='Size of storage of the new VM', type=int, default=20)
    parser.add_argument('--ip', dest='ip_address', help='Static IP address of the new VM', type=str, required=True)
    parser.add_argument('--spec', dest='spec', type=str, help='Spec of the VM. Choose from "large", "medium", "small". ')
    return parser

def print_progress(message):
    # Print the progress in red color
    print(RED + '[' + str(datetime.datetime.now()) + '] ' + message + END)

def create_vm_on_host(args):
    # 1. ssh to the host machine and use 'virt-install' to create KVM on the host machine
    # 2. Wait for MAAS to detect the new machine and get the system id of the new VM on MAAS. 
    # Return: str ---> system ID of the new VM on maas 
    vm_name = args.name
    cmd = 'virt-install --noautoconsole --autostart --name="{}" --os-type=linux --os-variant=ubuntu16.04 --vcpu={} --cpu=Broadwell-noTSX-IBRS --memory={} --disk=pool=default,size={},sparse=no --network=bridge=br-internal --network=bridge=br-external --boot=network,hd'.format(vm_name, args.core, args.ram, args.storage)
    ssh = 'ssh -t {}@{}'.format(args.username, args.host_ip)
    print_progress('Creating KVM on host ({})'.format(args.host_ip))
    cmd_output = exec_cmd(ssh + ' ' + cmd)
    print(cmd_output)
    print_progress('Getting MAC address of VM')
    mac = get_mac_address(vm_name)
    print('MAC Address: ', mac)

    print_progress('Getting system ID of VM')
    system_id = get_systemID_from_mac(mac)
    while system_id == None:
        print('.', end='', flush=True)
        system_id = get_systemID_from_mac(mac)
    print('System ID: ', system_id)
    return system_id


def get_mac_address(vm_name):
    # Use virsh to get the MAC address of the new VM on host machine, this MAC address is used to find the right VM on MAAS. 
    cmd = 'virsh domiflist {}'.format(vm_name)
    ssh = 'ssh -t {}@{}'.format(args.username, args.host_ip)
    cmd_output = exec_cmd(ssh + ' ' + cmd)
    mac = re.search(r'([0-9A-F]{2}[:-]){5}([0-9A-F]{2})', cmd_output, re.I).group()
    return mac

def get_systemID_from_mac(mac):
    # Use the MAC address to get the system ID of the new VM. 
    cmd = 'vm_info mac {}'.format(mac)
    cmd_output = exec_cmd(cmd)
    id_index = cmd_output.find('System ID:')
    if id_index == -1: return None
    system_id = cmd_output[id_index + len('System ID:') + 1: id_index + len('System ID:') + 7]
    return system_id

def exec_cmd(cmd):
    # Execute the command and return the ouput message. 
    # Input: str
    # Output: str
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output, err = p.communicate()
    p_status = p.wait()
    return output.decode('utf-8')

def setup_vm(args, system_id):
    # Setup the power type of the VM so that it can be controled by MAAS. 
    print_progress('Configuring VM')
    cmd = 'maas ctld machine update {} hostname={} power_type=virsh power_parameters_power_address=qemu+ssh://{}@{}/system power_parameters_power_id={}'.format(system_id, args.name, args.username, args.host_ip, args.name)
    cmd_output = exec_cmd(cmd)

def get_vm_status(system_id): 
    # Get the current status of the VM on MAAS. 
    cmd = 'vm_info id {}'.format(system_id)
    cmd_output = exec_cmd(cmd)
    status_idx = cmd_output.find('Status: ')
    status = cmd_output[status_idx + len('Status: '): cmd_output.find('\n', status_idx)]
    return status

def get_vm_interface(args):
    # Get the interface information of the VM. 
    cmd = 'vm_info name {} --link'.format(args.name)
    cmd_output = exec_cmd(cmd).strip().replace("\'", '\"')
    #print(cmd_output)
    link = json.loads(cmd_output)
    return link


def commission(args, system_id):
    print_progress('Commissioning')
    cmd = 'maas ctld machine commission {}'.format(system_id)
    cmd_output = exec_cmd(cmd)
    status = get_vm_status(system_id)
    print(status, end='', flush=True)
    last_status = status
    while(status != 'Ready'):
        status = get_vm_status(system_id)
        if status == last_status: print('.', end='', flush=True)
        else: print(status, end='', flush=True)
        last_status = status
    print()
    return

def set_static_ip(args, system_id): 
    print_progress('Setting static IP')
    link = get_vm_interface(args)
    cmd = 'maas {} interface unlink-subnet {} {} id={}'.format(args.username, system_id, link['interface_id'], link['link_id'])
    cmd_output = exec_cmd(cmd)
    # print(cmd_output)
    cmd = 'maas {} interface link-subnet {} {} mode=static subnet={} ip_address={}'.format(args.username, system_id, link['interface_id'], link['cidr'], args.ip_address)
    cmd_output = exec_cmd(cmd)
    ip = args.ip_address
    while 'IP address is already in use.' in cmd_output:
        #ip = input('IP address is already in use. Please enter a new one: ')
        print('{} is already in use. Trying next IP...'.format(ip))
        ip = next_ip(ip)
        cmd = 'maas {} interface link-subnet {} {} mode=static subnet={} ip_address={}'.format(args.username, system_id, link['interface_id'], link['cidr'], ip)
        cmd_output = exec_cmd(cmd)
    print('VM set to static IP {}'.format(ip))
    args.ip_address = ip
    #print(cmd_output)
    return

def next_ip(ip): 
    # Find the next IP  ex.'10.99.100.101' -> '10.99.100.102',  '10.99.100.254' -> '10.99.101.1'
    # input: str ex. '10.99.100.101'
    # output: str ex. '10.99.100.102'
    ip = ip.split('.')
    ip = list(map(int, ip))
    ip[3] += 1
    for i in range(3, 0, -1):
        if ip[i] >= 255:
            ip[i-1] += 1
            ip[i] = 1
    ip = list(map(str, ip))
    return '.'.join(ip)


def deploy(args, system_id):
    print_progress('Deploying')
    cmd = 'maas ctld machine deploy {}'.format(system_id)
    cmd_output = exec_cmd(cmd)
    status = get_vm_status(system_id)
    print(status, end='', flush=True)
    last_status = status
    while(status != 'Deployed'):
        status = get_vm_status(system_id)
        if status == last_status: print('.', end='', flush=True)
        else: print(status, end='', flush=True)
        last_status = status
    print()
    return 

def config_spec(args):
    spec = args.spec
    if spec:
        if spec.lower() == 'small':
            args.core = 2
            args.ram = 3840
            args.storage = 50
        if spec.lower() == 'medium':
            args.core = 4
            args.ram = 7680
            args.storage = 100
        if spec.lower() == 'large':
            args.core = 8
            args.ram = 15360
            args.storage = 200



if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()

    config_spec(args)
    system_id = create_vm_on_host(args)
    setup_vm(args, system_id)
    commission(args, system_id)
    set_static_ip(args, system_id)
    deploy(args, system_id)
    print_progress('VM successfully installed!!!')
    print('VM is at {}'.format(args.ip_address))
    print('You can access it with "ssh ctld@{}"'.format(args.ip_address))

