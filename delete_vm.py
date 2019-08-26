#!/usr/bin/python3
import argparse
import subprocess

def create_parser():
	parser = argparse.ArgumentParser(description='Tool to delete a VM')
	parser.add_argument('name', type=str, help='Name of the VM that you want to delete')
	parser.add_argument('host', type=str, help='Host IP of the VM that you are deleting')
	return parser

def exec_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output, err = p.communicate()
    p_status = p.wait()
    return output.decode('utf-8')

def delete_vm(args):
	vm_name = args.name
	host_ip = args.host
	delete_vm_on_maas(vm_name)
	delete_vm_on_host(vm_name, host_ip)



def delete_vm_on_maas(vm_name):
	print('Deleting VM on MAAS')
	system_id = get_systemID_from_name(vm_name)
	cmd = 'maas ctld machine delete {}'.format(system_id)
	output = exec_cmd(cmd)


def delete_vm_on_host(vm_name, host_ip):
	print('Deleting VM on host')
	ssh = 'ssh -t ctld@{}'.format(host_ip)
	cmd = 'virsh destroy {}'.format(vm_name)
	output = exec_cmd(ssh + ' ' + cmd)
	print(output)
	cmd = 'virsh undefine {} --remove-all-storage'.format(vm_name)
	output = exec_cmd(ssh + ' ' + cmd)
	print(output)

def get_systemID_from_name(vm_name):
	cmd = 'vm_info name {}'.format(vm_name)
	output = exec_cmd(cmd)
	id_index = output.find('System ID:')
	if id_index == -1: return None
	system_id = output[id_index + len('System ID:') + 1: id_index + len('System ID:') + 7]
	return system_id



if __name__ == '__main__':
	parser = create_parser()
	args = parser.parse_args()
	delete_vm(args)