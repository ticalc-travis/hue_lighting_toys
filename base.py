#!/usr/bin/env python3

import argparse
import signal
import sys

import phue                     # https://github.com/studioimaginaire/phue


USAGE_NO_LIGHTS_MSG = """If no lights are specified, all lights found on the bridge will be
used in the effect.

"""

USAGE_FIRST_RUN_MSG = """The first time this script is run on a device, it may be necessary to
press the button on the bridge before running the script so that it
can be registered to access the bridge and lighting system.

"""


class ProgramArgumentError(Exception):
    pass


class BaseProgram():
    """Skeleton class for a program that connects to a Philips Hue bridge
    and parses some basic command-line arguments such as a list of
    lights to use
    """

    usage_description = "This is a test program."

    usage_epilog = USAGE_NO_LIGHTS_MSG + USAGE_FIRST_RUN_MSG

    def __init__(self, raw_arguments=None):
        """Parse raw arguments and initialize connection to Hue bridge"""
        arg_parser = self._get_arg_parser()
        self.opts = arg_parser.parse_args(raw_arguments)
        self.bridge = self._get_bridge()
        self.lights = self._get_lights()
        if not self.lights:
            raise ProgramArgumentError('No lights available')

    def _get_arg_parser(self):
        """Create a pertinent argument parser and return it"""
        parser = argparse.ArgumentParser(
            description=self.usage_description,
            epilog=self.usage_epilog)
        parser.add_argument(
            '-ln', '--light-number',
            help='use light(s) numbered %(metavar)s',
            dest='lights', action='append', type=int, metavar='LIGHT-NUM',
            nargs='+')
        parser.add_argument(
            '-l', '--light-name',
            help='use light(s) named %(metavar)s',
            dest='lights', action='append', type=str,
            metavar='LIGHT-NAME', nargs='+')
        parser.add_argument(
            '-b', '--bridge',
            help='Hue bridge IP or hostname',
            dest='bridge_address')
        parser.add_argument(
            '-bu', '--bridge-username',
            help='Hue bridge username',
            dest='bridge_username')
        parser.add_argument(
            '-bc', '--bridge-config',
            help='path of config file for bridge connection parameters',
            dest='bridge_config')
        return parser

    def _get_bridge(self):
        """Establish and return a phue Bridge object to use"""
        return phue.Bridge(ip=self.opts.bridge_address,
                           username=self.opts.bridge_username,
                           config_file_path=self.opts.bridge_config)

    def _get_lights(self):
        """Find and return a list of light objects representing the lights
        specified by the user, in the order specified
        """
        if self.opts.lights:
            lights = []
            for ll in self.opts.lights:
                for li in ll:
                    try:
                        lights.append(self.bridge[li])
                    except KeyError:
                        print("Warning: No such light: %s" %
                              repr(li), file=sys.stderr)
        else:
            lights = self.bridge.get_light_objects()
        return lights

    def turn_on_lights(self):
        """Turn on all lights to be used"""
        for L in self.lights:
            self.bridge.set_light(L.light_id, 'on', True)

    def run(self):
        """Start the program"""
        print('The following lights were specified:')
        for L in self.lights:
            print(L.name)
        print('\nThe lights will now be turned on.')
        self.turn_on_lights()
        print('\nDone!')


def run_with_quit_handler(program):
    """Run a program that catches KeyboardInterrupt and then terminates with
    the appropriate return code on *nix
    """
    try:
        program.run()
    except KeyboardInterrupt:
        sys.exit(signal.SIGINT + 128)    # Terminate quietly on ^C


if __name__ == '__main__':
    try:
        p = BaseProgram()
    except ProgramArgumentError as e:
        print('Error: %s' % e, file=sys.stderr)
        sys.exit(2)
    else:
        run_with_quit_handler(p)
