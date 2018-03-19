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
        hue_group.add_argument(
            '-nh', '--no-hue',
            dest='no_hue', action='store_true',
            help="don't set hue during run")

        sat_group = self.opt_parser.add_mutually_exclusive_group()
        sat_group.add_argument(
            '-sr', '--saturation-range',
            dest='sat_range', nargs=2,
            type=self.int_within_range(MIN['sat'], MAX['sat']),
            metavar=('L', 'H'), default=[MIN['sat'], MAX['sat']],
            help='restrict the generated saturation range (%d to %d) from L to H' % (
                MIN['sat'], MAX['sat']))
        sat_group.add_argument(
            '-ns', '--no-sat',
            dest='no_sat', action='store_true',
            help="don't set saturation during run")

        bri_group = self.opt_parser.add_mutually_exclusive_group()
        bri_group.add_argument(
            '-br', '--brightness-range',
            dest='bri_range', nargs=2,
            type=self.int_within_range(MIN['bri'], MAX['bri']),
            metavar=('L', 'H'), default=[MIN['bri'], MAX['bri']],
            help='restrict the generated saturation range (%d to %d) from L to H' % (
                MIN['bri'], MAX['bri']))
        bri_group.add_argument(
            '-nb', '--no-bri',
            dest='no_bri', action='store_true',
            help="don't set brightness during run")

    def add_cycle_time_opt(self, default=100):
        """Append cycle time option to parser"""
        self.opt_parser.add_argument(
            '-t', '--cycle-time',
            dest='cycle_time', type=self.int_within_range(0, None),
            metavar='DECISECONDS', default=default,
            help='cycle time in tenths of a second (default: %(default)s)')

    def get_random_hue(self):
        """Generate and return a random hue value according to passed program arguments"""
        if self.opts.normalized_random_hue:
            return random_hue()
        return random.randint(*self.opts.hue_range)

    def get_random_parms(self, last_parms=None):
        """Generate and return a randomized light parameter dict according to
        passed program arguments, based on last_parms if specified
        (relevant with hue/saturation/brightness grouping)
        """
        is_update = last_parms is not None
        parms = {} if not is_update else last_parms.copy()
        # Update the parameter if it's not disabled (-nh/-ns/-nb) and if
        # last_parms was not given (meaning generate a new parm dict
        # with all paramters) or the parameter is not “grouped” across lamps
        if not self.opts.no_hue and not (is_update and self.opts.group_hue):
            parms['hue'] = self.get_random_hue()
        if not self.opts.no_sat and not (is_update and self.opts.group_sat):
            parms['sat'] = random.randint(*self.opts.sat_range)
        if not self.opts.no_bri and not (is_update and self.opts.group_bri):
            parms['bri'] = random.randint(*self.opts.bri_range)
        return parms

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
            parms = self.get_random_parms()
            for light in self.lights:
                self.bridge.set_light(
                    light, parms,
                    transitiontime=self.opts.cycle_time)
                parms = self.get_random_parms(parms)
            decisleep(self.opts.cycle_time)


def main():
    default_run(FadingColorsProgram)
