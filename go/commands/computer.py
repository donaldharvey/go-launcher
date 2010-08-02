from go.commands import Command
from functools import partial
import dbus
import dbus.glib
session_bus = dbus.SessionBus()
system_bus = dbus.SystemBus()

class DBusCommand(Command):
    method_name = ''
    path = ''
    bus_name = ''
    bus = session_bus
    def __init__(self):
        interface = self.bus.get_object(self.bus_name, self.path)
        self.method = partial(interface.get_dbus_method(self.method_name, dbus_interface=self.bus_name), reply_handler=lambda *args: False, error_handler=lambda e: False)
    def execute(self, exec_string):
        self.method()

class LockScreenCommand(DBusCommand):
    name = 'lock'
    nice_name = 'Lock Screen'
    caption = 'Lock your screen.'
    bus_name = 'org.gnome.ScreenSaver'
    path = '/'
    method_name = 'Lock'

class LogOutCommand(DBusCommand):
    name = 'logout'
    nice_name = 'Logout'
    caption = 'End your session and return to the login screen.'
    bus_name = 'org.gnome.SessionManager'
    path = '/org/gnome/SessionManager'
    method_name = 'Logout'
    def execute(self, exec_string):
        self.method(1) # Mode 1 means that no confirmation is shown.

class SuspendCommand(DBusCommand):
    name = 'suspend'
    nice_name = 'Suspend'
    caption = 'Suspend the computer.'
    bus = system_bus
    bus_name = 'org.freedesktop.UPower'
    path = '/org/freedesktop/UPower'
    method_name = 'Suspend'

class HibernateCommand(DBusCommand):
    name = 'hibernate'
    nice_name = 'Hibernate'
    caption = 'Hibernate the computer.'
    bus = system_bus
    bus_name = 'org.freedesktop.UPower'
    path = '/org/freedesktop/UPower'
    method_name = 'Hibernate'

class DummyCommand(Command):
    name = 'dummy'
    nice_name = 'Dummy'
    caption = 'A dummy command'
    def execute(self, exec_string):
        print 'Dummy Command!', exec_string

commands = [
    LockScreenCommand,
    LogOutCommand,
    SuspendCommand,
    HibernateCommand,
    DummyCommand
]