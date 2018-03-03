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

import random
import time

from hue_toys.base import (BaseProgram, default_run)
from hue_toys.phue_helper import MIN, MAX, decisleep, random_hue


class FadingColorsProgram(BaseProgram):
    """Produce a Philips Hue lighting random color fade effect."""

    def add_range_parse_opts(self):
        """Append hue/saturation/brightness range options to parser"""
        hue_group = self.opt_parser.add_mutually_exclusive_group()
        hue_group.add_argument(
            '-r', '--normalized-random-hue', action='store_true',
            help='use alternate algorithm for selecting random hues more "evenly"')
        hue_group.add_argument(
            '-hr', '--hue-range',
            dest='hue_range', nargs=2,
            type=self.int_within_range(MIN['hue'], MAX['hue']), metavar=('L', 'H'),
            default=[MIN['hue'], MAX['hue']],
            help='restrict the generated hue range (%d to %d) from L to H' % (
                MIN['hue'], MAX['hue']))
        self.opt_parser.add_argument(
            '-sr', '--saturation-range',
            dest='sat_range', nargs=2,
            type=self.int_within_range(MIN['sat'], MAX['sat']),
            metavar=('L', 'H'), default=[MIN['sat'], MAX['sat']],
            help='restrict the generated saturation range (%d to %d) from L to H' % (
                MIN['sat'], MAX['sat']))
        self.opt_parser.add_argument(
            '-br', '--brightness-range',
            dest='bri_range', nargs=2,
            type=self.int_within_range(MIN['bri'], MAX['bri']),
            metavar=('L', 'H'), default=[MIN['bri'], MAX['bri']],
            help='restrict the generated saturation range (%d to %d) from L to H' % (
                MIN['bri'], MAX['bri']))

    def add_cycle_time_opt(self, default=100):
        """Append cycle time option to parser"""
        self.opt_parser.add_argument(
            '-t', '--cycle-time',
            dest='cycle_time', type=self.int_within_range(0, None),
            metavar='DECISECONDS', default=default,
            help='cycle time in tenths of a second (default: %(default)s)')

    def get_random_hue(self):
        """Generate and return a random hue value according to passed command arguments"""
        if self.opts.normalized_random_hue:
            return random_hue()
        return random.randint(*self.opts.hue_range)

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.add_cycle_time_opt()

        self.opt_parser.add_argument(
            '-gh', '--group-hue',
            dest='group_hue', action='store_true',
            help='match the same hue among all lights')
        self.opt_parser.add_argument(
            '-gs', '--group-saturation',
            dest='group_sat', action='store_true',
            help='match the same saturation among all lights')
        self.opt_parser.add_argument(
            '-gb', '--group-brightness',
            dest='group_bri', action='store_true',
            help='match the same brightness among all lights')

        self.add_range_parse_opts()

    def main(self):
        self.turn_on_lights()

        while True:
            hue = self.get_random_hue()
            sat = random.randint(*self.opts.sat_range)
            bri = random.randint(*self.opts.bri_range)
            for light in self.lights:
                self.bridge.set_light(
                    light, {'hue': hue, 'sat': sat, 'bri': bri},
                    transitiontime=self.opts.cycle_time)
                if not self.opts.group_hue:
                    hue = random.randint(*self.opts.hue_range)
                if not self.opts.group_sat:
                    sat = random.randint(*self.opts.sat_range)
                if not self.opts.group_bri:
                    bri = random.randint(*self.opts.bri_range)
            decisleep(self.opts.cycle_time)


def main():
    default_run(FadingColorsProgram)
