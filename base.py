#!/usr/bin/env python3

"""Base classes and utilities for programs dealing with Philips Hue smart
lights
"""

import argparse
import signal
import sys
import textwrap

import phue                     # https://github.com/studioimaginaire/phue


class ProgramArgumentError(Exception):
    """Exception signaling incorrect command-line arguments that prevent
    program execution
    """
    pass


class BaseProgram():
    """A sample CLI program for the Philips Hue system that takes
    command-line arguments and connects to the given bridge and operates
    on the specified lights
    """

    usage_first_run_msg = '''The first time this script is run on a device, it may be necessary to
press the button on the bridge before running the script so that it can
be registered to access the bridge and lighting system.'''

    usage_light_order_msg = '''Lights will be sequenced in the order specified.'''

    usage_no_lights_msg = '''If no lights are specified, all lights found on the bridge will be
used in the effect.'''

    def __init__(self, raw_arguments=None):
        """Parse raw arguments and initialize connection to Hue bridge"""
        self.init_arg_parser()
        self.opts = self.opt_parser.parse_args(raw_arguments)

        self.bridge = self.get_bridge()
        self.lights = self.get_lights()
        if not self.lights:
            raise ProgramArgumentError('No lights available')

    def get_description(self):
        """Get formatted program description"""
        return textwrap.fill(self.__doc__)

    def get_usage_epilog(self):
        """Construct and return program epilogue for usage message"""
        return '\n\n'.join(
            [self.usage_no_lights_msg, self.usage_first_run_msg])

    def add_bridge_opts(self):
        """Add generic bridge arguments to argument parser"""
        self.opt_parser.add_argument(
            '-b', '--bridge',
            help='Hue bridge IP or hostname',
            dest='bridge_address')
        self.opt_parser.add_argument(
            '-bu', '--bridge-username',
            help='Hue bridge username',
            dest='bridge_username')
        self.opt_parser.add_argument(
            '-bc', '--bridge-config',
            help='path of config file for bridge connection parameters',
            dest='bridge_config')

    def add_light_opts(self):
        """Add generic light-listing arguments to argument parser"""
        self.opt_parser.add_argument(
            '-ln', '--light-number',
            help='use light(s) numbered %(metavar)s',
            dest='lights', action='append', type=int, metavar='LIGHT-NUM',
            nargs='+')
        self.opt_parser.add_argument(
            '-l', '--light-name',
            help='use light(s) named %(metavar)s',
            dest='lights', action='append', type=str,
            metavar='LIGHT-NAME', nargs='+')

    def add_opts(self):
        """Add program's command arguments to argument parser"""
        self.add_bridge_opts()
        self.add_light_opts()

    def init_arg_parser(self):
        """Set up the command argument parser"""
        self.opt_parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=self.get_description(),
            epilog=self.get_usage_epilog())
        self.add_opts()

    def get_bridge(self):
        """Establish and return a phue Bridge object to use"""
        return phue.Bridge(ip=self.opts.bridge_address,
                           username=self.opts.bridge_username,
                           config_file_path=self.opts.bridge_config)

    def get_lights(self):
        """Find and return a list of light objects representing the lights
        specified by the user, in the order specified
        """
        if self.opts.lights:
            lights = []
            for light in [light for sublist in self.opts.lights
                          for light in sublist]:
                try:
                    lights.append(self.bridge[light])
                except KeyError:
                    print("Warning: No such light: %s" %
                          repr(light), file=sys.stderr)
        else:
            lights = self.bridge.get_light_objects()
        return lights

    def turn_on_lights(self):
        """Turn on all lights to be used"""
        for light in self.lights:
            self.bridge.set_light(light.light_id, 'on', True)

    def run(self):
        """Start the program"""
        print('The following lights were specified:')
        for light in self.lights:
            print(light.name)
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

def default_run(prog_class):
    """Create an instance of prog_class, displaying command argument errors
    if they occur, and supply a return code for this condition or keyboard
    interrupts.
    """
    try:
        prog = prog_class()
    except ProgramArgumentError as e:
        print('Error: %s' % e, file=sys.stderr)
        sys.exit(2)
    else:
        run_with_quit_handler(prog)


if __name__ == '__main__':
    default_run(BaseProgram)
