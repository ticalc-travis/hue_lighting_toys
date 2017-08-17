#!/usr/bin/env python3

import argparse
import random
import sys
import time

import phue                     # https://github.com/studioimaginaire/phue

from base import (BaseProgram, ProgramArgumentError, run_with_quit_handler)


class FadingColorsProgram(BaseProgram):

    usage_description = "Produce a Philips Hue lighting random color fade effect."

    def _get_range_parser(self):
        """Return a parser with options for hue/saturation/brightness ranges"""
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            '-hr', '--hue-range',
            help='restrict the generated hue range (0 to 65535) from L to H',
            dest='hue_range', nargs=2, type=int, metavar=('L', 'H'),
            default=[0, 65535])
        parser.add_argument(
            '-sr', '--saturation-range',
            help='restrict the generated saturation range (0 to 255) from L to H',
            dest='sat_range', nargs=2, type=int, metavar=('L', 'H'),
            default=[0, 255])
        parser.add_argument(
            '-br', '--brightness-range',
            help='restrict the generated saturation range (1 to 254) from L to H',
            dest='bri_range', nargs=2, type=int, metavar=('L', 'H'),
            default=[1, 254])
        return parser

    def _get_arg_parser(self):
        parent = BaseProgram._get_arg_parser(self)
        parent2 = self._get_range_parser()
        parser = argparse.ArgumentParser(parents=[parent, parent2],
                                         add_help=False)
        parser.add_argument(
            '-t', '--cycle-time',
            help='''use a speed of %(metavar)s tenths of a second per color cycle
(default: %(default)s)')''',
            dest='cycle_time', type=int, metavar='DECISECONDS', default=100)
        parser.add_argument(
            '-gh', '--group-hue',
            help='match the same hue among all lights',
            dest='group_hue', action='store_true')
        parser.add_argument(
            '-gs', '--group-saturation',
            help='match the same saturation among all lights',
            dest='group_sat', action='store_true')
        parser.add_argument(
            '-gb', '--group-brightness',
            help='match the same brightness among all lights',
            dest='group_bri', action='store_true')
        return parser

    def run(self):
        while True:
            h = random.randint(*self.opts.hue_range)
            s = random.randint(*self.opts.sat_range)
            b = random.randint(*self.opts.bri_range)
            for L in self.lights:
                self.bridge.set_light(
                    L.light_id, {'hue': h, 'sat': s, 'bri': b},
                    transitiontime=self.opts.cycle_time)
                if not self.opts.group_hue:
                    h = random.randint(*self.opts.hue_range)
                if not self.opts.group_sat:
                    s = random.randint(*self.opts.sat_range)
                if not self.opts.group_bri:
                    b = random.randint(*self.opts.bri_range)
            time.sleep(self.opts.cycle_time / 10)


if __name__ == '__main__':
    try:
        p = FadingColorsProgram()
    except ProgramArgumentError as e:
        print('Error: %s' % e, file=sys.stderr)
        sys.exit(2)
    else:
        run_with_quit_handler(p)
