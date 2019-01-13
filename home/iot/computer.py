import subprocess

import paramiko
from wakeonlan import send_magic_packet


class Computer:
    widget = {
        'buttons': (
            {
                'text': 'Wake',
                'method': 'wake',
                'class': 'btn-success'
            },
            {
                'text': 'Sleep',
                'method': 'sleep',
                'class': 'btn-warning'
            },
            {
                'text': 'Shut Down',
                'method': 'power',
                'config': {'state': 'off'},
                'class': 'btn-danger'
            },
            {
                'text': 'Reboot',
                'method': 'restart',
                'class': 'btn-danger'
            },
        )
    }

    def __init__(self, mac, host=None, port=None, manual_interface=None, keyfile="~/.ssh/id_rsa", username="root",
                 password=None, os: str = "linux", wakeonlan: str = "native"):
        self.password = password
        self.username = username
        self.keyfile = keyfile
        self.mac = mac
        self.host = host
        self.port = port
        self.interface = manual_interface
        self.os = os
        self.wakeonlan = wakeonlan

    def on(self):
        self.wake()

    def off(self):
        self.power('off')

    def restart(self):
        self.power('restart')

    def reboot_to(self, boot_option: int):
        if boot_option >= 0:
            self.run_command('sudo grub-reboot ' + boot_option)
            self.run_command('sudo grub2-reboot ' + boot_option)
            self.restart()

    def wake(self):
        if self.wakeonlan in ('etherwake', 'ether-wake'):
            iface = []
            if self.interface:
                iface = ['-i ' + self.interface]
            for i in range(3):
                subprocess.run(['sudo', '/usr/sbin/ether-wake', *iface, self.mac])
        elif self.wakeonlan == 'wakeonlan':
            for i in range(3):
                subprocess.run(['sudo', '/usr/bin/wakeonlan', self.mac])
        elif self.wakeonlan == 'native':
            for i in range(3):
                send_magic_packet(self.mac, ip_address=self.host)
        else:
            raise NotImplementedError("No valid wake-on-LAN method chosen")

    def sleep(self):
        if self.os == "linux":
            self.run_command('sudo systemctl suspend')
        elif self.os == "linux-old":
            self.run_command('pm-suspend')
        else:
            raise NotImplementedError

    def power(self, state: str = 'on'):
        if state == 'on':
            self.wake()
        elif state == 'off':
            self.run_command('sudo poweroff')
        elif state in ['sleep', 'suspend']:
            self.sleep()
        elif state in ['restart', 'reboot']:
            self.run_command('sudo reboot')
        else:
            raise NotImplementedError

    def run_command(self, command: str, user: str = "", password: str = "", keyfile: str = "") -> str:
        username = user or self.username
        password = password or self.password
        keyfile = keyfile or self.keyfile
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.host,
                    self.port,
                    username,
                    password,
                    key_filename=keyfile)
        r = ssh.exec_command(command)[2].readlines()
        ssh.close()
        return r
