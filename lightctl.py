#!/usr/bin/env python3

import sys

from base import (BaseProgram, default_run)


class LightCLIControlProgram(BaseProgram):
    """Command-line utility to control Hue lights"""

    def add_keep_state_opt(self):
        """Do nothing (the “keep state” option does not apply to this program,
        so it shouldn't be present, and no state restoration should be
        done)
        """
        return

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.opt_parser.add_argument(
            '-n', '--on',
            dest='on', action='store_const', const=True,
            help='turn lights on')
        self.opt_parser.add_argument(
            '-f', '--off',
            dest='on', action='store_const', const=False,
            help='turn lights off')
        self.opt_parser.add_argument(
            '-b', '--brightness',
            dest='bri', type=int,
            help='set brightness (1 to 254)')
        self.opt_parser.add_argument(
            '-u', '--hue',
            dest='hue', type=int,
            help='set hue (0 to 65535)')
        self.opt_parser.add_argument(
            '-s', '--saturation',
            dest='sat', type=int,
            help='set saturation (1 to 254)')
        self.opt_parser.add_argument(
            '-x', '--xy',
            dest='xy', nargs=2, type=float, metavar=('X', 'Y'),
            help='set X, Y color coordinates (fractional value from 0 to 1)')
        self.opt_parser.add_argument(
            '-c', '--ct', '--color-temp',
            dest='ct', type=int, metavar='MIREDS',
            help='set color temperature in mireds/mireks')
        self.opt_parser.add_argument(
            '-k', '--kelvin',
            dest='ctk', type=int, metavar='KELVIN',
            help='set color temperature in Kelvin')

        self.opt_parser.add_argument(
            '-t', '--transition-time',
            dest='transitiontime', type=int, metavar='DECISECONDS',
            help='use a transition time of %(metavar)s tenths of a second')

    def validate_opts(self):
        if self.opts.ct is not None and self.opts.ct <= 0:
            self.opt_parser.error('Color temperature must be at least 1 mired')

    def main(self):
        self.validate_opts()

        cmd = {}

        for param in ('on', 'bri', 'hue', 'sat', 'xy', 'ct', 'ctk',
                      'transitiontime'):
            value = getattr(self.opts, param)
            if value is not None:
                cmd[param] = value

        if cmd:
            self.bridge.set_light(self.lights, cmd)
        else:
            self.opt_parser.error('no action specified')


if __name__ == '__main__':
    default_run(LightCLIControlProgram)
