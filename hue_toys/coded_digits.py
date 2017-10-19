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

import math
import time

from hue_toys.base import (BaseProgram, default_run)
from hue_toys.chasing_colors import ChasingColorsProgram


## Light parameters used to encode each character/digit ##

DIGITS_DEFAULT = 'bright'

# This dict may be edited to change the light parameters that represent
# each digit or to add new digit “schemes”
DIGITS = {
    'dim': {
        '0': {'on': True, 'ct': 250, 'bri': 1},
        '1': {'on': True, 'hue': 46014, 'sat': 255, 'bri': 1},
        '2': {'on': True, 'hue': 7500, 'sat': 180, 'bri': 1},
        '3': {'on': True, 'hue': 24155, 'sat': 254, 'bri': 1},
        '4': {'on': True, 'hue': 10434, 'sat': 254, 'bri': 32},
        '5': {'on': True, 'hue': 0, 'sat': 255, 'bri': 1},
        '6': {'on': True, 'hue': 3901, 'sat': 255, 'bri': 32},
        '7': {'on': True, 'hue': 48913, 'sat': 218, 'bri': 1},
        '8': {'on': True, 'hue': 39280, 'sat': 236, 'bri': 32},
        '9': {'on': True, 'hue': 58368, 'sat': 254, 'bri': 1},
        # Default encoding for unrecognized characters; also used for
        # “strobe” transitions between characters
        None: {'on': False},
    },
    'bright': {
        '0': {'on': True, 'ct': 250, 'bri': 92},
        '1': {'on': True, 'hue': 46014, 'sat': 255, 'bri': 64},
        '2': {'on': True, 'hue': 7500, 'sat': 180, 'bri': 64},
        '3': {'on': True, 'hue': 24155, 'sat': 254, 'bri': 128},
        '4': {'on': True, 'hue': 10434, 'sat': 254, 'bri': 192},
        '5': {'on': True, 'hue': 0, 'sat': 255, 'bri': 92},
        '6': {'on': True, 'hue': 3901, 'sat': 255, 'bri': 128},
        '7': {'on': True, 'hue': 48913, 'sat': 218, 'bri': 64},
        '8': {'on': True, 'hue': 39280, 'sat': 236, 'bri': 128},
        '9': {'on': True, 'hue': 58368, 'sat': 254, 'bri': 128},
        # Default encoding for unrecognized characters; also used for
        # “strobe” transitions between characters
        None: {'on': False},
    },
}


class CodedDigitsProgram(ChasingColorsProgram):
    """Blink out a series of digits encoded using colors."""

    schemes = DIGITS

    default_scheme = DIGITS_DEFAULT

    def add_main_opts(self):
        """Add all program options to command parser except for the digits
        parameter
        """

        BaseProgram.add_opts(self)

        self.add_cycle_time_opt(default=10)

        self.opt_parser.add_argument(
            '-s', '--switch-time',
            dest='switch_time', type=self.int_within_range(-1, None),
            metavar='DECISECONDS', default=2,
            help='''If there are more digits to transmit than lights, display the "blank"
color on all lights for %(metavar)s tenths of a second before each digit
flash (default: %(default)s . 0 makes it as short as possible; -1
disables it entirely.''')
        self.opt_parser.add_argument(
            '-fs', '--force-switch-time',
            dest='force_switch', action='store_true',
            help='''always use a switch time after the digit flash, even if there are
enough lights to display all digits at once''')
        self.opt_parser.add_argument(
            '-p', '--pad',
            dest='padded', action='store_const', const=True,
            help='''always reset all lights to the "blank" color when the sequence
finishes, instead of only when there are more digits than lights to
transmit''')
        self.opt_parser.add_argument(
            '-np', '--no-pad',
            dest='padded', action='store_const', const=False,
            help='never reset lights to the "blank" color when the sequence finishes')
        self.opt_parser.add_argument(
            '-c', '--scheme',
            dest='scheme', type=str, choices=sorted(DIGITS.keys()), default=DIGITS_DEFAULT,
            help='use the chosen color scheme')

    def add_opts(self):
        self.add_main_opts()
        self.opt_parser.add_argument(
            'digits', type=str,
            help='the sequence of digits to flash')

    @staticmethod
    def group_digits(digits, num_lights):
        """Group a string of digits into a sequence of digit strings, each the
        same length as num_lights, space-padded if necessary
        """
        size_with_pad = math.ceil(len(digits) / num_lights) * num_lights
        padded_digits = '{:>{}}'.format(digits, size_with_pad)
        digit_groups = [padded_digits[i:i+num_lights]
                        for i in range(0, size_with_pad, num_lights)]
        return digit_groups

    def flash_digits(self, digits):
        """Flash the lights in the code designated by the digit string “digits”."""
        digit_groups = self.group_digits(digits, len(self.lights))
        digit_cmds = self.schemes[self.opts.scheme]
        have_multiple_groups = len(digit_groups) > 1
        use_padding = self.opts.padded
        if use_padding is None:
            use_padding = have_multiple_groups

        last_digit_group = ''
        for digit_group in digit_groups:

            # Unless it's disabled with switch time of -1, do a brief
            # transition blink between digit groups if there's more than
            # one “page” of digits to blink or the blink was forced with
            # the switch_time command option, *and* the last digit group
            # flashed exactly matches the new one to flash
            if ((have_multiple_groups or self.opts.force_switch) and
                    self.opts.switch_time >= 0 and
                    digit_group == last_digit_group):
                self.bridge.set_light_optimized(
                    self.lights, digit_cmds[None], transitiontime=0)
                time.sleep(self.opts.switch_time / 10)

            # Now flash the actual digits
            for digit, light in zip(digit_group, self.lights):
                cmd = digit_cmds.get(digit, digit_cmds[None])
                self.bridge.set_light_optimized(
                    light, cmd, transitiontime=0)
            last_digit_group = digit_group
            time.sleep(self.opts.cycle_time / 10)

        # Now, handle the final pad flash if this is turned on
        if use_padding:
            self.bridge.set_light_optimized(
                self.lights, digit_cmds[None], transitiontime=0)
            time.sleep(self.opts.cycle_time / 10)

    def main(self):
        """Call self.flash_digits with digit string given on command line"""
        self.flash_digits(self.opts.digits)


def main():
    default_run(CodedDigitsProgram)
