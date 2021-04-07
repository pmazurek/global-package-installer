import subprocess
import platform
import sys
import os
import io
import re
import time

import requests

from gpi import settings


def execute_command(command):
    command = command.split(' ')
    return subprocess.check_output(command).decode('UTF-8').strip()


def execute_command_interactive(command):
    try:
        response = subprocess.check_output(
            command,
            shell=True,
            executable='/bin/bash'
        ).decode(encoding='UTF-8')
        return response.strip()
    except subprocess.CalledProcessError as e:
        print('Command failed. ')
        print(str(e))
        exit(1)


def execute_command_with_live_output(command):
    command = command.split(' ')
    process = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE)
    while True:
      output = process.stdout.readline()
      if process.poll() is not None:
        break
      if output:
        print(output.decode('UTF-8'))
    rc = process.poll()


class PipPort:

    commands = {
        'install': 'pip install {}',
        'uninstall': 'pip uninstall -y {}',
        'list-installed': 'pip list',
        'show': 'fzf'
    }

    index_url = 'https://pypi.org/simple/'

    def __init__(self):
        self.dot_dir = os.path.expanduser(settings.DOT_DIR)
        self.cache_path = self.dot_dir + '/pypi.cache'

    def list_packages(self, installed):
        if installed:
            raw_lines = execute_command(self.commands['list-installed'])
            lines = raw_lines.split("\n")[2:] # ignoring top two lines
            packages = []
            for line in lines:
                packages.append(line.strip().split()[0])

            return packages

        if not os.path.exists(self.cache_path):
            print('Generating pip cache')
            response = requests.get(self.index_url)
            all_packages = re.findall('href="/simple/([^/]*)/', response.text)
            self.save_package_cache(all_packages)
            return all_packages
        else:
            with open(self.cache_path) as f:
                packages = f.read().splitlines()

            return packages

    def save_package_cache(self, packages):
        f = open(self.cache_path, 'w')
        f.write("\n".join(packages))
        f.flush()
        os.fsync(f.fileno())
        f.close()

    def entrypoint(self, uninstall=False):
        if uninstall:
            packages = self.list_packages(installed=True)
            fuzzysearch_bash_command = 'echo "{}" | {}'.format(
                "\n".join(packages),
                self.commands['show']
            )
            chosen_package = execute_command_interactive(fuzzysearch_bash_command)
            execute_command_with_live_output(
                self.commands['uninstall'].format(chosen_package)
            )
        else:
            packages = self.list_packages(installed=False)
            fuzzysearch_bash_command = 'cat "{}" | {}'.format(
                self.cache_path,
                self.commands['show']
            )
            chosen_package = execute_command_interactive(fuzzysearch_bash_command)
            execute_command_with_live_output(
                self.commands['install'].format(chosen_package)
            )

class UbuntuPort:

    commands = {
        'install': 'sudo apt install -y {}',
        'uninstall': 'sudo apt remove -y {}',
        'list-available': 'sudo apt list',
        'list-installed': 'sudo apt list --installed',
        'show': """fzf --border --preview 'sudo apt-cache show {} |  grep -E "^Package|^Version|^Homepage|^Description-en|^ "'"""
    }

    def __init__(self):
        self.dot_dir = os.path.expanduser(settings.DOT_DIR)
        self.cache_path = os.path.expanduser(settings.CACHE_PATH)

        self.check_privileges()
        self.ensure_dot_dir_exists()
        
    def ensure_dot_dir_exists(self):
        if not os.path.exists(self.dot_dir):
            os.makedirs(self.dot_dir)

    def save_package_cache(self, packages):
        f = open(self.cache_path, 'w')
        f.write("\n".join(packages))
        f.flush()
        os.fsync(f.fileno())
        f.close()

    def list_packages(self, installed=False):
        print('Building package cache... ')
        if installed:
            raw_packages = execute_command(self.commands['list-installed'])
        else:
            raw_packages = execute_command(self.commands['list-available'])

        raw_packages = raw_packages.split('\n')

        ignore_arch = 'i386' if platform.architecture()[0] == '64bit' else 'amd64'
        packages = []

        for row in raw_packages:
            if ignore_arch in row:
                continue

            if '/' in row:
                entry = ''
                entry += row.split('/')[0]
                packages.append(entry)

        return packages

    def check_privileges(self):
        return True
        if execute_command('whoami') != 'root':
            print("You must run this as root. Exiting.")
            exit(1)

    def get_fzf_choice(self):
        fuzzysearch_bash_command = 'cat "{}" | {}'.format(
            self.cache_path,
            self.commands['show']
        )
        return execute_command_interactive(fuzzysearch_bash_command)

    def entrypoint(self, uninstall=False):
        if uninstall:
            installed=True
            command = self.commands['uninstall']
        else:
            installed=False
            command = self.commands['install'] 

        packages = self.list_packages(installed=installed)
        self.save_package_cache(packages)

        chosen_package = self.get_fzf_choice()
        
        execute_command_with_live_output(
            command.format(chosen_package)
        )


def detect_package_manager():
    try:
        execute_command('sudo yum --help')
        return 'yum'
    except subprocess.CalledProcessError:
        pass

    try:
        execute_command('sudo apt-get --help')
        return 'apt'
    except subprocess.CalledProcessError:
        pass

    raise Exception('Unable to detect package manager.')


package_manager_mappings = {
    'apt': UbuntuPort,
    'pip': PipPort,
}

def entrypoint_install():
    main_entrypoint(uninstall=False)

def entrypoint_remove():
    main_entrypoint(uninstall=True)

def main_entrypoint(uninstall):
    if len(sys.argv) > 1 and sys.argv[1] in ['pip']:
        package_manager = sys.argv[1]
    else:
        package_manager = detect_package_manager()

    port_class = package_manager_mappings[package_manager]
    port = port_class()

    port.entrypoint(uninstall=uninstall)

