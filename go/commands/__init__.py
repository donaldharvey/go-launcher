import os
import sys
from inspect import isclass

class Command(object):
    name = ''
    aliases = []
    def lookup(self, search_string):
        raise NotImplementedError
    def execute(self, exec_string):
        raise NotImplementedError


def find_commands():
    discovered_commands = {}
    for filename in os.listdir(os.path.abspath(os.path.dirname(__file__))):
        if filename.endswith('.py') and filename != '__init__.py':
            name = 'go.commands.%s' % filename.split('.')[0]
            __import__(name)
            module = sys.modules[name]
            if hasattr(module, 'commands'):
                for command in module.commands:
                    discovered_commands[command.name] = command()
    return discovered_commands

if __name__ == '__main__':
    c = find_commands()
