#!/usr/bin/env python3

"""Base classes and helper functions for programs dealing with Philips
Hue smart lights
"""

import argparse
import logging
import signal
import sys
import textwrap
from time import sleep

from phue_helper import ExtendedBridge

LOG_FORMAT = '%(asctime)s: %(message)s'


class BaseProgram():
    """A sample CLI program for the Philips Hue system that takes
    command-line arguments and connects to the given bridge and operates
    on the specified lights
    """

    usage_first_run_msg = '''The first time this script is run on a system, it may be necessary to
press the button on the bridge before running the script so that it can
be registered to access the bridge and lighting system.'''

    usage_light_order_msg = '''Lights will be sequenced in the order specified.'''

    usage_no_lights_msg = '''If no lights are specified, all lights found on the bridge will be
used in the effect.'''

    def __init__(self, raw_arguments=None, bridge_retries=10,
                 bridge_retry_wait=1):
        """Parse raw arguments and initialize connection to Hue bridge

        Args:
        raw_arguments: List of CLI args to arg parser
        bridge_retries: Max number of retries if bridge command fails
        bridge_retry_wait: Seconds to wait between bridge retries
        """
        self.init_arg_parser()
        self.opts = self.opt_parser.parse_args(raw_arguments)

        self.bridge = self.get_bridge()
        self.lights = self.get_lights()
        if not self.lights:
            self.opt_parser.error('no lights available')
        self.bridge_retries = bridge_retries
        self.bridge_retry_wait = bridge_retry_wait

        # Set up verbose output if specified
        if getattr(self.opts, 'verbose', False):
            logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
        self.log = logging.getLogger(__name__)

    def get_description(self):
        """Get formatted program description"""
        return textwrap.fill(self.__doc__)

    def get_usage_epilog(self):
        """Construct and return program epilogue for usage message"""
        return '\n\n'.join(
            [self.usage_no_lights_msg, self.usage_first_run_msg])

    @staticmethod
    def int_within_range(min_limit, max_limit):
        """Return a function that converts a string to an int, raising
        argparse.ArgumentTypeError on failure or if the resulting value
        is less than min_limit or more than max_limit. A min_limit of
        None means no lower limit, and a max_limit of None means no
        upper limit.
        """
        def int_range_validator(str_):
            try:
                int_ = int(str_)
            except ValueError:
                raise argparse.ArgumentTypeError(
                    'invalid int value: %s' % str_)

            err_msg = ''
            if ((min_limit is not None and max_limit is not None)
                    and (int_ < min_limit or int_ > max_limit)):
                err_msg = 'from %d to %d' % (min_limit, max_limit)
            elif min_limit is not None and int_ < min_limit:
                err_msg = '%d or higher' % min_limit
            elif max_limit is not None and int_ > max_limit:
                err_msg = '%d or lower' % max_limit
            if err_msg:
                raise argparse.ArgumentTypeError(
                    'value must be %s: %d' % (err_msg, int_))
            return int_

        return int_range_validator

    @staticmethod
    def positive_float():
        """Return a function that converts a string to a float, raising
        argparse.ArgumentTypeError on failure or if the resulting value
        is not greater than zero.
        """
        def positive_float_validator(str_):
            try:
                float_ = float(str_)
            except ValueError:
                raise argparse.ArgumentTypeError(
                    'invalid floating point value: %s' % str_)
            if float_ <= 0:
                raise argparse.ArgumentTypeError(
                    'value must be greater than 0: %s' % float_)
            return float_

        return positive_float_validator

    def add_bridge_opts(self):
        """Add generic bridge arguments to argument parser"""
        self.opt_parser.add_argument(
            '-B', '--bridge',
            dest='bridge_address',
            help='Hue bridge IP or hostname')
        self.opt_parser.add_argument(
            '-Bu', '--bridge-username',
            dest='bridge_username',
            help='Hue bridge username')
        self.opt_parser.add_argument(
            '-Bc', '--bridge-config',
            dest='bridge_config',
            help='path of config file for bridge connection parameters')

    def add_light_opts(self):
        """Add generic light-listing arguments to argument parser"""
        self.opt_parser.add_argument(
            '-l', '--light-id',
            dest='lights', action='append', type=int, metavar='LIGHT-NUM',
            nargs='+',
            help='use light(s) with ID number %(metavar)s')
        self.opt_parser.add_argument(
            '-ln', '--light-name',
            dest='lights', action='append', type=str, metavar='LIGHT-NAME',
            nargs='+',
            help='use light(s) named %(metavar)s')

    def add_verbose_opt(self):
        """Add generic verbosity option"""
        self.opt_parser.add_argument(
            '-v', '--verbose',
            dest='verbose', action='store_true',
            help='output extra info/debugging log messages')

    def add_restore_opt(self):
        """Add option to restore lights; default action will be not to restore"""
        self.opt_parser.add_argument(
            '--restore-lights',
            dest='restore_light_state', action='store_true',
            help='return lights to their original state on exit')

    def add_no_restore_opt(self):
        """Add option to not restore lights; default action will be restore"""
        self.opt_parser.add_argument(
            '--no-restore-lights',
            dest='restore_light_state', action='store_false',
            help='do not return lights to their original state on exit')

    def add_light_state_opt(self):
        """Add option to either restore or not restore light state on program
        exit, if applicable
        """
        self.add_no_restore_opt()

    def add_opts(self):
        """Add program's command arguments to argument parser"""
        self.add_verbose_opt()
        self.add_bridge_opts()
        self.add_light_opts()
        self.add_light_state_opt()

    def init_arg_parser(self):
        """Set up the command argument parser"""
        self.opt_parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=self.get_description(),
            epilog=self.get_usage_epilog())
        self.add_opts()

    def get_bridge(self):
        """Establish and return a phue Bridge object to use"""
        return ExtendedBridge(ip=self.opts.bridge_address,
                              username=self.opts.bridge_username,
                              config_file_path=self.opts.bridge_config)

    def get_lights(self):
        """Find and return a list of light IDs representing the lights
        specified by the user, in the order specified
        """
        if self.opts.lights:
            lights = []
            for light in [light for sublist in self.opts.lights
                          for light in sublist]:
                if light in self.bridge:
                    lights.append(light)
                else:
                    print("%s: warning: no such light: %s" %
                          (sys.argv[0], repr(light)), file=sys.stderr)
        else:
            lights = [o.light_id for o in self.bridge.get_light_objects()]
        return lights

    def turn_on_lights(self):
        """Turn on all lights to be used"""
        self.bridge.set_light(self.lights, 'on', True)

    def turn_off_lights(self):
        """Turn off all lights to be used"""
        self.bridge.set_light(self.lights, 'on', False)

    def main(self):
        """Perform the main program procedure"""
        print('The following lights were specified:')
        for light in self.lights:
            print(self.bridge[light].name)
        print('\nThe lights will now be turned on.')
        self.turn_on_lights()
        sleep(5)
        print('\nThe lights will now be turned off.')
        self.turn_off_lights()
        sleep(5)
        print('\nHave a nice day!')

    def run(self):
        """Initialize, run the main program procedure, and clean up. Here, save
        the light state before starting, then restore it before
        termination if it should be done.
        """

        # Do not assume self.opts has restore_light_state, as this method
        # may be called by subclasses that did not install it as a
        # command option. If it isn't an option, don't restore, but let
        # the child class handle things.
        do_restore = getattr(self.opts, 'restore_light_state', False)

        if do_restore:
            light_state = self.bridge.collect_light_states(self.lights)

        try:
            self.main()
        finally:
            if do_restore:
                self.bridge.restore_light_states_retry(
                    self.bridge_retries, self.bridge_retry_wait,
                    self.lights, light_state, transitiontime=0)


def default_run(prog_class):
    """Create an instance of prog_class, displaying command argument errors
    if they occur, and supply a return code for this condition or keyboard
    interrupts.
    """
    prog = prog_class()
    try:
        prog.run()
    except KeyboardInterrupt:
        sys.exit(signal.SIGINT + 128)    # Terminate quietly on ^C


if __name__ == '__main__':
    default_run(BaseProgram)
