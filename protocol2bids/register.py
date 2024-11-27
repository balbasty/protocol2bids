from importlib import import_module

V = 'protocol2bids.vendors'

REGISTER = {}


def register_parser(path):
    REGISTER[path] = import_module(f'{V}.{path}')


register_parser('siemens.va')
register_parser('siemens.vb')
register_parser('siemens.vd')
register_parser('siemens.ve')
# register_parser('siemens.xa')
# register_parser('philips.txt')
