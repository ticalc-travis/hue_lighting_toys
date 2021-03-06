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

import time

from hue_toys.base import (BaseProgram, default_run)
from hue_toys.phue_helper import (
    DEFAULT_TRANSITION_TIME, MIN, MAX, iconv_ct, decisleep)


TRANSITION_OVERHEAD = 4
"""An extra delay, in deciseconds, to add when waiting for transition
time to complete in order to roughly compensate for light command
execution delays
"""


class LightControlProgram(BaseProgram):
    """Command-line utility to control Hue lights"""

    usage_relative_args = '''Except with the -x/--xy option, numerical arguments may be prefixed
with a + or - to add or subtract the value from the light's current
setting instead of setting it directly to that value. Color temperature
will be limited to Hue's supported range of 153–500 mired or 2000–6535
Kelvin if such relative inputs are used, though setting absolute values
outside this range are allowed and will be simulated if necessary.'''

    def get_usage_epilog(self):
        return '\n\n'.join(
            [self.usage_no_lights_msg, self.usage_relative_args,
             self.usage_first_run_msg])

    def add_light_state_opt(self):
        # Light state restoration does not apply to this program
        return

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.opt_parser.add_argument(
            '-n', '--on',
            dest='on', action='store_const', const=(True, False),
            help='turn lights on')
        self.opt_parser.add_argument(
            '-f', '--off',
            dest='on', action='store_const', const=(False, False),
            help='turn lights off')
        self.opt_parser.add_argument(
            '-o', '--toggle',
            dest='on', action='store_const', const=(True, True),
            help='toggle lights on or off')
        self.opt_parser.add_argument(
            '-b', '--brightness',
            dest='bri', type=self.relative_int(MIN['bri'], MAX['bri']),
            help='set brightness (%d to %d)' % (MIN['bri'], MAX['bri']))
        self.opt_parser.add_argument(
            '-u', '--hue',
            dest='hue', type=self.relative_int(MIN['hue'], MAX['hue']),
            help='set hue (%d to %d)' % (MIN['hue'], MAX['hue']))
        self.opt_parser.add_argument(
            '-s', '--saturation',
            dest='sat', type=self.relative_int(MIN['sat'], MAX['sat']),
            help='set saturation (%d to %d)' % (MIN['sat'], MAX['sat']))
        self.opt_parser.add_argument(
            '-x', '--xy',
            dest='xy', nargs=2, type=self.fractional_float(), metavar=('X', 'Y'),
            help='set X, Y color coordinates (fractional value from %s to %s)' % (
                MIN['xy'], MAX['xy']))
        self.opt_parser.add_argument(
            '-c', '--ct', '--color-temp',
            dest='ct', type=self.relative_int(MIN['xct'], MAX['xct']),
            metavar='MIREDS',
            help='set color temperature in mireds/mireks')
        self.opt_parser.add_argument(
            '-k', '--kelvin',
            dest='ctk', type=self.relative_int(MIN['xctk'], MAX['xctk']),
            metavar='KELVIN',
            help='set color temperature in Kelvin')

        self.opt_parser.add_argument(
            '-i', '--incandescent',
            dest='inc', type=self.relative_int(MIN['inc'], MAX['inc']),
            metavar='BRI',
            help='''set brightness to %(metavar)s and set lamp color to simulate an
                 incandescent bulb dimmed to that brightness level''')

        self.opt_parser.add_argument(
            '-t', '--transition-time',
            dest='transitiontime', type=int, metavar='DECISECONDS',
            help='use a transition time of %(metavar)s tenths of a second')

        self.opt_parser.add_argument(
            '-w', '--wait',
            action='store_true',
            help='wait for the transition time to elapse before exiting')

    def handle_relative(self, light_id, param, value):
        """Take a relative value to change light parameter param by and return
        the effective absolute value that that parameter should be set
        to to effect the change.
        """
        state = self.bridge.get_light(light_id)['state']
        if param == 'ctk':
            new_value = iconv_ct(state['ct']) + value
            new_value = max(min(new_value, MAX['ctk']), MIN['ctk'])
        elif param == 'inc':
            new_value = max(min(state['bri'] + value, MAX['inc']), MIN['inc'])
        elif param == 'on':
            new_value = not state['on']
        else:
            new_value = max(min(state[param] + value, MAX[param]), MIN[param])
        return new_value

    def main(self):
        cmd = {}

        for light in self.lights:
            for param in ('on', 'bri', 'hue', 'sat', 'xy', 'ct', 'ctk',
                          'inc', 'transitiontime'):
                value = getattr(self.opts, param)
                if isinstance(value, tuple):
                    value, relative = getattr(self.opts, param)
                    if relative:
                        value = self.handle_relative(light, param, value)
                if value is not None:
                    cmd[param] = value

            if not cmd or cmd.keys() == {'transitiontime'}:
                self.opt_parser.error('no action specified')
            else:
                self.bridge.set_light(light, cmd)

        if self.opts.wait:
            if self.opts.transitiontime is None:
                transition_time = DEFAULT_TRANSITION_TIME
            else:
                transition_time = self.opts.transitiontime
            decisleep(transition_time + TRANSITION_OVERHEAD)


def main():
    default_run(LightControlProgram)
