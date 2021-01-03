#!/usr/bin/python3
import argparse
import string
import sys


def generate_config(config_file, template, mapping):
    try:
        with open(config_file, 'w') as fd:
            fd.write(string.Template(template).substitute(mapping))
    except IOError as err:
        raise ValueError("Failed to generate config file: %s" % err)


def create_mapping(dut):
    mapping = {'dut': dut}
    return mapping


def load_template(template_file):
    try:
        with open(template_file, 'r') as fd:
            template = fd.read()
        return template
    except IOError as err:
        raise ValueError("Failed to load template: %s" % err)


def parse_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-t', '--template', required=True,
        help="config template file"
    )
    parser.add_argument(
        '-d', '--device', required=True, dest='dut',
        help="android device under test"
    )
    parser.add_argument(
        '-o', '--output-config-file', default='config.json', dest='out',
        help="config file to generate"
    )

    return parser.parse_args(sys.argv[1:])


def main():
    opts = parse_cli()
    template = load_template(opts.template)
    mapping = create_mapping(opts.dut)
    generate_config(opts.out, template, mapping)


if __name__ == "__main__":
    try:
        main()
    except ValueError as err:
        print(err)
        sys.exit(1)