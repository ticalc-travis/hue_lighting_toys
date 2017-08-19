#!/usr/bin/env python3

import math
import time

from base import (BaseProgram, default_run)
from chasing_colors import ChasingColorsProgram


## Light parameters used to encode each character/digit ##

DIGITS_DEFAULT = 'bright'

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
            dest='switch_time', type=int, metavar='DECISECONDS', default=2,
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
            dest='scheme', type=str, choices=DIGITS.keys(), default=DIGITS_DEFAULT,
            help='use the chosen color scheme')

    def add_opts(self):
        self.add_main_opts()
        self.opt_parser.add_argument(
            'digits',
            help='the sequence of digits to flash',
            type=str)

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

        for digit_group in digit_groups:
            if self.opts.switch_time >= 0 and (have_multiple_groups or
                                               self.opts.force_switch):
                self.bridge.set_light(self.lights, digit_cmds[None],
                                      transitiontime=0)
                time.sleep(self.opts.switch_time / 10)
            for digit, light in zip(digit_group, self.lights):
                cmd = digit_cmds.get(digit, digit_cmds[None])
                self.bridge.set_light(light, cmd, transitiontime=0)
            time.sleep(self.opts.cycle_time / 10)
        if use_padding:
            self.bridge.set_light(self.lights, digit_cmds[None],
                                  transitiontime=0)
            time.sleep(self.opts.cycle_time / 10)

    def run(self):
        """Call self.flash_digits with digit string given on command line"""
        self.flash_digits(self.opts.digits)


if __name__ == '__main__':
    default_run(CodedDigitsProgram)
