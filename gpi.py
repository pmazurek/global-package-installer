import subprocess
import platform
import sys
import os
import io
import time


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


class UbuntuPort:

    INSTALL_COMMAND = 'sudo apt install -y {}'
    UNINSTALL_COMMAND = 'sudo apt remove -y {}'
    DOT_DIR = '~/.upi'
    CACHE_PATH = DOT_DIR + '/available_packages.cache'

    def __init__(self):
        self.DOT_DIR = os.path.expanduser(self.DOT_DIR)
        self.CACHE_PATH = os.path.expanduser(self.CACHE_PATH)

        self.check_privileges()
        self.ensure_dot_dir_exists()
        
    def ensure_dot_dir_exists(self):
        if not os.path.exists(self.DOT_DIR):
            os.makedirs(self.DOT_DIR)

    def save_package_cache(self, packages):
        f = open(self.CACHE_PATH, 'w')
        f.write("\n".join(packages))
        f.flush()
        os.fsync(f.fileno())
        f.close()

    def list_packages(self, installed=False):
        print('Building package cache... ')
        if installed:
            raw_packages = execute_command('sudo apt list --installed')
        else:
            raw_packages = execute_command('sudo apt list')

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
            self.CACHE_PATH,
            'fzf'
        )
        return execute_command_interactive(fuzzysearch_bash_command)

    def entrypoint(self, uninstall=False):
        if uninstall:
            installed=True
            command = self.UNINSTALL_COMMAND
        else:
            installed=False
            command = self.INSTALL_COMMAND

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
}

if __name__ == '__main__':
    package_manager = detect_package_manager()
    port_class = package_manager_mappings[package_manager]
    port = port_class()
    uninstall = False
    if len(sys.argv) > 1 and sys.argv[1] == '-u':
        uninstall = True

    port.entrypoint(uninstall=uninstall)

