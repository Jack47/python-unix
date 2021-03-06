# -*- coding: utf-8 -*-

import os.path as path
import unix
#from unix.linux import Linux

NO_DEBCONF = "DEBIAN_FRONTEND='noninteractive'"
"""Disable ncurse configuration interface for APT packages."""

NETCONF_FILE = '/etc/network/interfaces'
NETCONF_DIR = '/etc/network/interfaces.d/'

def Deb(host, root=''):
    unix.isvalid(host)

    if unix.ishost(host, 'DebHost'):
        if unix.ishost(host, 'Local'):
            new_host = unix.Local()
        else:
            new_host = unix.Remote()
        new_host.__dict__.update(host.__dict__)
        return Deb(new_host, root)

    host = unix.linux.Linux(host, root)

    class DebHost(host.__class__):
        def __init__(self, root=''):
            host.__class__.__init__(self, root)
            self.__dict__.update(host.__dict__)
            # Check this is a Debian-like system.


        @property
        def distribution(self):
            return self.execute('lsb_release -i')[1].split(':')[1].strip()


        @property
        def release(self):
            return self.execute('lsb_release -r')[1].split(':')[1].strip()


        @property
        def codename(self):
            return self.execute('lsb_release -c')[1].split(':')[1].strip()


        def set_hostname(self, hostname):
            try:
                self.write('/etc/hostname', hostname)
                return [True, '', '']
            except IOError as ioerr:
                return [False, '', ioerr]


        def set_network(self, interfaces):
            main_conf = ['auto lo', 'iface lo inet loopback']

            # For each interface, creating a configuration file
            interfaces_conf = []
            for index, interface in enumerate(interfaces):
                interface_name = 'eth%s' % index

                interface_conf = [
                    'auto %s' % interface_name,
                    'iface %s inet static' % interface_name,
                    '    address %s' % interface['address'],
                    '    netmask %s' % interface['netmask'],
                ]
                if 'gateway' in interface:
                    interface_conf.insert(
                        -2,
                        '    gateway %s' % interface['gateway']
                    )

                interfaces_conf.append(interface_conf)

            if self.distribution == 'Ubuntu' and float(self.release) < 11.04:
                for interface_conf in interfaces_conf:
                    main_conf.append('')
                    main_conf.extend(interface_conf)
            else:
                # Add a line
                main_conf.extend(['', 'source %s*' % NETCONF_DIR])

                # Creating the directory where configuration files of each
                # interfaces are stored.
                output = self.mkdir(NETCONF_DIR)
                if not output[0]:
                    return [False, '', output[2]]

                for index, interface_conf in enumerate(interfaces_conf):
                    try:
                        self.write(
                            path.join(NETCONF_DIR, 'eth%s' % index),
                            '\n'.join(interface_conf)
                        )
                    except IOError as ioerr:
                        return [False, '', ioerr]

            # Creating main configuration file.
            try:
                self.write(NETCONF_FILE, '\n'.join(main_conf))
            except IOError as ioerr:
                return [False, '', ioerr]

            return [True, '', '']


        def check_pkg(self, package):
            status, stdout = self.execute('dpkg -l')[:2]
            for line in stdout.split('\n'):
                if status and line.find(package) != -1 and line[0] != 'r':
                    return True
            return False


        def add_key(self, filepath):
            remote_filepath = path.join('/tmp', path.basename(filepath))
            self.get(filepath, remote_filepath)
            return self.execute('apt-key add %s' % remote_filepath)


        def add_repository(self, filepath):
            return self.get(filepath, path.join(
                '/etc/apt/sources.list.d',
                path.basename(filepath)
            ))


        def apt_update(self):
            return self.execute('aptitude update')


        def apt_install(self, packages, interactive=True):
            return self.execute(
                '%s aptitude install -y %s' % (NO_DEBCONF, ' '.join(packages)),
                interactive
            )


        def apt_search(self, package, interactive=True):
            status, stdout, stderr = self.execute(
                "aptitude search %s" % package, interactive
            )
            if status:
                for line in stdout.split("\n"):
                    if line.find(package) != -1:
                        return True

            return False


        def apt_remove(self, packages, purge=False):
            apt_command = 'purge -y' if purge else 'remove -y'
            return self.execute(
                '%s aptitude %s %s' % (NO_DEBCONF, apt_command, ' '.join(packages))
            )


        def deb_install(self, filepath, force=False):
            command = '-i --force-depends' if force else '-i'
            return self.execute('%s dpkg %s %s' % (NO_DEBCONF, command, filepath))

    return DebHost(root)
