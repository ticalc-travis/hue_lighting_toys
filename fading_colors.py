#!/usr/bin/env python3

import random
import time

from base import (BaseProgram, default_run)


class FadingColorsProgram(BaseProgram):
    """Produce a Philips Hue lighting random color fade effect."""

    def add_range_parse_opts(self):
        """Append hue/saturation/brightness range options to parser"""
        self.opt_parser.add_argument(
            '-hr', '--hue-range',
            dest='hue_range', nargs=2, type=int, metavar=('L', 'H'),
            default=[0, 65535],
            help='restrict the generated hue range (0 to 65535) from L to H')
        self.opt_parser.add_argument(
            '-sr', '--saturation-range',
            dest='sat_range', nargs=2, type=int, metavar=('L', 'H'),
            default=[1, 254],
            help='restrict the generated saturation range (1 to 254) from L to H')
        self.opt_parser.add_argument(
            '-br', '--brightness-range',
            dest='bri_range', nargs=2, type=int, metavar=('L', 'H'),
            default=[1, 254],
            help='restrict the generated saturation range (1 to 254) from L to H')

    def add_cycle_time_opt(self, default=100):
        """Append cycle time option to parser"""
        self.opt_parser.add_argument(
            '-t', '--cycle-time',
            help='cycle time in tenths of a second (default: %(default)s)',
            dest='cycle_time', type=int, metavar='DECISECONDS',
            default=default)

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

    def run(self):
        self.turn_on_lights()

        while True:
            hue = random.randint(*self.opts.hue_range)
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
            time.sleep(self.opts.cycle_time / 10)


if __name__ == '__main__':
    default_run(FadingColorsProgram)
