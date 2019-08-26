#!/usr/bin/python3
import sys
import argparse
import json
import os
import subprocess

def create_parser():
    parser = argparse.ArgumentParser(description='show info of the VM')
    sp_action = parser.add_subparsers()

    sp_list = sp_action.add_parser('list', help='Show all VM on MAAS')
    sp_list.set_defaults(func=list_vm)

    sp_name = sp_action.add_parser('name', help='Show info of name')
    sp_name.add_argument('name', metavar='name', type=str, help='name')
    sp_name.add_argument('--link', action='store_true', default=False, help='Show only information of main link')
    sp_name.set_defaults(func=show_info_of_name)

    sp_id = sp_action.add_parser('id', help='Show info of id')
    sp_id.add_argument('id', metavar='id', type=str, help='id')
    sp_id.set_defaults(func=show_info_of_id)

    sp_mac = sp_action.add_parser('mac', help='Show info of specific MAC address')
    sp_mac.add_argument('mac', metavar='mac', type=str, help='mac')
    sp_mac.set_defaults(func=show_info_of_mac)

    sp_file = sp_action.add_parser('file', help='Show info from file')
    sp_file.add_argument('filename', metavar='filename', type=str, help='filename')
    sp_file.add_argument('--link', action='store_true', default=False, help='Show only information of main link')
    sp_file.set_defaults(func=show_info_from_file)

    return parser

def show_info_from_file(args):
    data = get_info_from_file(args.filename)
    if len(data) == 0: 
        print('No such VM!!!')
        return 
    if args.link: 
        links = get_links(data[0])
        static_link = get_main_link(links)
        print(static_link)
    else: print_info(data[0])
    return 

def show_info_of_id(args):
    data = get_info_of_id(args.id)
    if len(data) == 0: 
        print('No such VM!!!')
        return 
    print_info(data[0])
    return 

def show_info_of_name(args):
    data = get_info_of_name(args.name)
    if len(data) == 0: 
        print('No such VM!!!')
        return 
    if args.link: 
        links = get_links(data[0])
        static_link = get_main_link(links)
        print(static_link)
    else: print_info(data[0])
    return 

def show_info_of_mac(args):
    data = get_all_vm_info()
    for d in data:
        f = flatten_the_data(d)
        mac = f.get('mac_address', None)
        name = f.get('system_id', None)
        if mac == args.mac: 
            print_info(d)
        elif args.mac == 'all': 
            print(name, ':', mac)
    #print(data)

def list_vm(args):
    data = get_all_vm_info()
    for d in data:
        f = flatten_the_data(d)
        name = f.get('hostname')
        system_id = f.get('system_id')
        ip = f.get('ip_addresses')
        print('Name:', name)
        print('System ID:', system_id)
        print('IP:', ip)
        print('____________________')

def get_info_from_file(filename):
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except:
        print('File not found!!!')
        sys.exit(2)
    return data 

def get_all_vm_info():
    cmd = 'maas ctld nodes read'.format(id)
    output = exec_cmd(cmd)
    try:
        data = json.loads(output)
    except:
        print('No such VM!!!')
        sys.exit(3)
    return data

def get_info_of_id(id):
    cmd = 'maas ctld nodes read id={}'.format(id)
    output = exec_cmd(cmd)
    try:
        data = json.loads(output)
    except:
        print('No such VM!!!')
        sys.exit(3)
    return data

def get_info_of_name(name):
    cmd = 'maas ctld nodes read hostname={}'.format(name)
    output = exec_cmd(cmd)
    try:
        data = json.loads(output)
    except:
        print('No such VM!!!')
        sys.exit(3)
    return data

def exec_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output, err = p.communicate()
    p_status = p.wait()
    return output


def flatten_the_data(data):
    flatten_data = {}
    for key, value in data.items():
        if isinstance(value, dict):
            flatten_data.update(flatten_the_data(value))
        else:
            flatten_data[key] = value
    return flatten_data

def get_links(data):
    links = []
    for interface in data.get('interface_set', None):
        #print(interface)
        if len(interface['links']) == 0: continue
        link = interface['links'][0]
        #print(link)
        if link != {}: links.append({'interface_id': interface.get('id', 'None'), 'link_id': link.get('id', 'None'), 'mode': link.get('mode', 'None'), 'ip_address': link.get('ip_address', 'None'), 'cidr': link['subnet']['cidr']})
    return links

def get_main_link(links):
    for link in links: 
        if link['mode'] == 'auto' or link['mode'] == 'static': return link
    if len(links): return links[0]

def print_info(data):
    #print(data['interface_set'])
    links = get_links(data)
    #print(links)
    data = flatten_the_data(data)
    print('============Basic Info=============')
    print('Hostname: {}'.format(data.get('hostname', 'None')))
    print('System ID: {}'.format(data.get('system_id', 'None')))
    print('Owner: {}'.format(data.get('owner', 'None')))
    print('Status: {}'.format(data.get('status_name', 'None')))
    print('CPU Model: {}'.format(data.get('cpu_model', 'None')))
    print('Number of CPU: {}'.format(data.get('cpu_count', 'None')))
    print('Memory: {} MB'.format(data.get('memory', 'None')))
    total_storage = data['blockdevice_set'][0]['size'] if data.get('blockdevice_set') else 0.0
    remain_storage = data['blockdevice_set'][0]['used_size'] if data.get('blockdevice_set') else 0.0
    usage = remain_storage/total_storage if remain_storage != 0.0 else 0.0
    print('Storage: {:.2%} ({}/{} GB)'.format(usage, remain_storage/1e9, total_storage/1e9))
    print('OS: {} '.format(data.get('osystem', 'None')))
    print('Power Type: {} '.format(data.get('power_type', 'None')))
    print('==============Network==============')
    print('IP Addresses: {}'.format(data.get('ip_addresses', 'None')))
    print('MAC Address: {}'.format(data.get('mac_address', 'None')))
    print('=============Interfaces============')
    for link in links:
        print('Interface ID: {}'.format(link['interface_id']))
        print('Link ID: {}'.format(link['link_id']))
        print('Mode: {}'.format(link['mode']))
        print('IP Address: {}'.format(link['ip_address']))
        print('CIDR: {}'.format(link['cidr']))
        print('------------------------------')


if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else: 
        parser.print_help()
        sys.exit(1)
