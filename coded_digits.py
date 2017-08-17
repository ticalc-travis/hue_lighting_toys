#!/usr/bin/env python3

import argparse
import math
import random
import signal
import sys
import time

import phue                     # https://github.com/studioimaginaire/phue

from base import (BaseProgram, default_run)
from fading_colors import FadingColorsProgram


# The light parameters used to encode each character/digit
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


class CodedDigitsProgram(FadingColorsProgram):

    usage_description = 'Blink out a series of digits encoded using colors.'

    schemes = DIGITS

    default_scheme = DIGITS_DEFAULT

    def _get_arg_parser(self):
        parent = BaseProgram._get_arg_parser(self)
        parser = argparse.ArgumentParser(parents=[parent], add_help=False)

        self._add_cycle_time_opt(parser, default=10)

        parser.add_argument(
            '-s', '--switch-time',
            help='If there are more digits to transmit than lights, display the "blank" color on all lights for %(metavar)s tenths of a second before each digit flash (default: %(default)s . 0 makes it as short as possible; -1 disables it entirely.',
            dest='switch_time', type=int, metavar='DECISECONDS', default=2)
        parser.add_argument(
            '-fs', '--force-switch-time', dest='force_switch',
            help='always use a switch time after the digit flash, even if there are enough lights to display all digits at once',
            action='store_true')
        parser.add_argument(
            '-p', '--pad',
            help='always reset all lights to the "blank" color when the sequence finishes, instead of only when there are more digits than lights to transmit',
            dest='padded', action='store_const', const=True)
        parser.add_argument(
            '-np', '--no-pad', dest='padded',
            help='never reset lights to the "blank" color when the sequence finishes',
            action='store_const', const=False)
        parser.add_argument(
            '-c', '--scheme',
            help='use the chosen color scheme',
            dest='scheme', type=str, choices=DIGITS.keys(),
            default=DIGITS_DEFAULT)
        parser.add_argument(
            'digits',
            help='the sequence of digits to flash',
            type=str)

        return parser

    def group_digits(self, digits, num_lights):
        size_with_pad = math.ceil(len(digits) / num_lights) * num_lights
        padded_digits = '{:>{}}'.format(digits, size_with_pad)
        digit_groups = [padded_digits[i:i+num_lights]
                        for i in range(0, size_with_pad, num_lights)]
        return digit_groups

    def run(self):
        digit_groups = self.group_digits(self.opts.digits,
                                         len(self.lights))
        digit_cmds = self.schemes[self.opts.scheme]
        have_multiple_groups = len(digit_groups) > 1
        use_padding = self.opts.padded
        if use_padding is None:
            use_padding = have_multiple_groups

        for digit_group in digit_groups:
            if self.opts.switch_time >= 0 and (have_multiple_groups or
                                          self.opts.force_switch):
                self.bridge.set_light([L.light_id for L in self.lights],
                                 digit_cmds[None], transitiontime=0)
                time.sleep(self.opts.switch_time / 10)
            for digit, light in zip(digit_group, self.lights):
                cmd = digit_cmds.get(digit, digit_cmds[None])
                self.bridge.set_light(light.light_id, cmd, transitiontime=0)
            time.sleep(self.opts.cycle_time / 10)
        if use_padding:
            self.bridge.set_light([L.light_id for L in self.lights],
                             digit_cmds[None], transitiontime=0)
            time.sleep(self.opts.cycle_time / 10)

if __name__ == '__main__':
    default_run(CodedDigitsProgram)
