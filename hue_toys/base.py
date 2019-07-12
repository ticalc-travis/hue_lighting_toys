#!/usr/bin/env python3

# Copyright (C) 2017 Travis Evans
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Base classes and helper functions for programs dealing with Philips
Hue smart lights
"""

import argparse
import logging
import signal
import sys
import textwrap
from time import sleep

from hue_toys.phue_helper import ExtendedBridge

LOG_FORMAT = '%(asctime)s [%(module)s] %(message)s'
SHUTDOWN_EXIT_CODE = 99


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
used.'''

    def __init__(self, raw_arguments=None, bridge_retries=10,
                 bridge_retry_wait=1):
        """Parse raw arguments and initialize connection to Hue bridge

        Args:
        raw_arguments: List of CLI args to arg parser
        bridge_retries: Max number of retries if bridge command fails
        bridge_retry_wait: Seconds to wait between bridge retries

        Other class attributes:
        bridge: Hue bridge object
        lights: List of lights to be handled by the program
        startup_brightness: Brightness that lamps should revert to on
            power loss when the power-failure restoration mode is
            temporarily disabled
        """
        self.init_arg_parser()
        self.opts = self.opt_parser.parse_args(raw_arguments)

        self.bridge = self.get_bridge()
        self.lights = self.get_lights()
        if not self.lights:
            self.opt_parser.error('no lights available')
        self.bridge_retries = bridge_retries
        self.bridge_retry_wait = bridge_retry_wait

        self.light_startup_mode = {}

        # Set up verbose output if specified
        verbose = getattr(self.opts, 'verbose', 0)
        if verbose == 1:
            logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
        if verbose == 2:
            logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)
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
    def fractional_float():
        """Return a function that converts a string to a float, raising
        argparse.ArgumentTypeError on failure or if the resulting value
        is not from 0.0 to 1.0.
        """
        def fractional_float_validator(str_):
            try:
                float_ = float(str_)
            except ValueError:
                raise argparse.ArgumentTypeError(
                    'invalid float value: %s' % str_)

            if not 0 <= float_ <= 1:
                raise argparse.ArgumentTypeError(
                    'value must be from 0.0 to 1.0: %s' % float_)
            return float_

        return fractional_float_validator

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

    def relative_int(self, min_limit, max_limit):
        """Return a function that accepts a string representing an int within
        min_limit and max_limit (works as with self.int_within_range),
        optionally prefixed with '+' or '-'. Return a tuple of the form
        (int_, relative), where relative is True if either '+' or '-'
        prefixes are used. In this case, int_ will be negative if the
        '-' prefix was given.

        This is intended to be used with arguments that allow the user
        to specify either an absolute value or a relative one that
        should be added or subtracted from some existing value.
        """
        def relative_int_validator(str_):
            relative = False
            prefix = str_[0]
            if prefix == '+' or prefix == '-':
                relative = True
                str_ = str_[1:]
            int_ = self.int_within_range(min_limit, max_limit)(str_)
            if prefix == '-':
                int_ = -int_
            return (int_, relative)

        return relative_int_validator

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
            dest='verbose', action='count',
            help='''output extra informational messages (and debug messages if specified
                 more than once)''')

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

    def add_power_fail_opt(self):
        """Add option to temporarily disable power-failure restore behavior"""
        self.opt_parser.add_argument(
            '-f', '--disable-power-fail-mode',
            action='store_true',
            help="temporarily disable power-failure restoration of light state while the effect runs (for Hue lights which support it)")

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
                try:
                    light_id = self.bridge[light].light_id
                except KeyError:
                    print("%s: warning: no such light: %s" %
                          (sys.argv[0], light), file=sys.stderr)
                else:
                    if light_id in lights:
                        print("%s: warning: duplicate light: %s" %
                              (sys.argv[0], light), file=sys.stderr)
                    else:
                        lights.append(light_id)
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

        # Do not assume self.opts has these options, as this method
        # may be called by subclasses that did not install them as
        # command options.
        do_restore = getattr(self.opts, 'restore_light_state', False)
        disable_power_fail = getattr(self.opts, 'disable_power_fail_mode', False)

        if do_restore:
            light_state = self.bridge.collect_light_states(self.lights)
        if disable_power_fail:
            self.disable_power_fail()

        try:
            self.main()
        finally:
            if disable_power_fail:
                self.enable_power_fail()
            if do_restore:
                self.bridge.restore_light_states(
                    self.lights, light_state, transitiontime=0)

    @property
    def _powerfail_brightness(self):
        return 254

    def disable_power_fail(self):
        """Set power-on mode of all supported lights in the used sequence to a
        fixed default based on self._powerfail_brightness. Remember the
        original power-on mode so it can be restored when
        enable_power_fail is called.
        """
        for light in self.lights:
            try:
                startup_config = self.bridge.api('lights/%s' % light)['config']['startup']
            except KeyError:
                self.log.info('Startup config not supported for light %s', light)
            else:
                startup_mode = startup_config['mode']
                if startup_mode in ['powerfail', 'lastonstate']:
                    self.log.info('Disabling light %s power-fail recovery mode', light)
                    self.light_startup_mode[light] = startup_mode
                    self.bridge.api('lights/%s/config' % light, {
                        'startup': {
                            'mode': 'custom',
                            'customsettings': {
                                'ct': 366,
                                'bri': self._powerfail_brightness,
                            }
                        }
                    })
                    # Delay a bit to avoid overloading Zigbee bandwidth
                    sleep(.1)
                else:
                    self.log.info('Light %s startup mode not powerfail or lastonstate; leaving alone',
                                  light)

    def enable_power_fail(self):
        """Restore power-on mode of lights to the value it was when
        self.disable_power_fail was called
        """
        for light, mode in self.light_startup_mode.items():
            self.log.info('Restoring startup mode for light %s to "%s"',
                          light, mode)
            self.bridge.api('lights/%s/config' % light,
                            {'startup': {'mode': mode}})
            # Delay a bit to avoid overloading Zigbee bandwidth
            sleep(.1)


class Shutdown(Exception):
    """Exception to signal immediate clean up and shutdown"""
    pass


def _start_shutdown(signum, frame):
    raise Shutdown()


def default_run(prog_class):
    """Create an instance of prog_class, displaying command argument errors
    if they occur, and supply a return code for this condition or keyboard
    interrupts.
    """
    signal.signal(signal.SIGTERM, _start_shutdown)
    prog = prog_class()
    try:
        prog.run()
    except KeyboardInterrupt:
        sys.exit(signal.SIGINT + 128)    # Terminate quietly on ^C
    except Shutdown:
        sys.exit(SHUTDOWN_EXIT_CODE)


def main():
    default_run(BaseProgram)
