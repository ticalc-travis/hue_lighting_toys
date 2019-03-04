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

from math import copysign
from time import time, sleep

from hue_toys.base import BaseProgram, default_run
from hue_toys.phue_helper import MIN, MAX


MIN_BRIDGE_CMD_INTERVAL = .3
"""Minimum number of seconds between commands sent to bridge"""


class IncandescentFadeProgram(BaseProgram):
    """Simulate an incandescent dimmer fade"""

    def add_light_state_opt(self):
        self.add_restore_opt()

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.opt_parser.add_argument(
            'start_brightness',
            type=self.int_within_range(MIN['inc']-1, MAX['inc']),
            help='the starting brightness level (%d–%d); %d is off' % (
                MIN['inc'], MAX['inc'], MIN['inc']-1))
        self.opt_parser.add_argument(
            'final_brightness',
            type=self.int_within_range(MIN['inc']-1, MAX['inc']),
            help='the ending brightness level (%d–%d); %d is off' % (
                MIN['inc'], MAX['inc'], MIN['inc']-1))
        self.opt_parser.add_argument(
            'fade_time', type=self.positive_float(),
            help='number of seconds to perform the fade')

        self.add_power_fail_opt()

    def _set_light_incan(self, level, transitiontime):
        """Set lights to the given brightness of “incandescent bulb” color, or
        turn them off if brightness level is one less than the minimum
        value normally considered valid on the Hue bridge.
        """
        if level >= MIN['inc']:
            cmd = {'on': True, 'inc': level}
        else:
            cmd = {'on': False}
        self.bridge.set_light(self.lights, cmd,
                              transitiontime=transitiontime)

    def fade(self, start_bri, final_bri, fade_time):
        """Perform an incandescent-like dimmer fade from brightness level
        start_bri to final_bri (which may be lower or higher than
        start_bri) over a total period of fade_time seconds.
        """
        self._set_light_incan(start_bri, 0)
        # Wait a short while, because apparently the last transition
        # time can get overridden if a new command with a different
        # transition time is sent too soon to the same light
        sleep(MIN_BRIDGE_CMD_INTERVAL)

        num_steps = abs(start_bri - final_bri)
        step_time = fade_time / num_steps
        start_time = time()

        while True:
            elapsed_time = min(time() - start_time, fade_time)
            bri = round(start_bri + copysign(elapsed_time / step_time,
                                             final_bri - start_bri))
            self.log.info('Setting brightness %d', bri)
            self._set_light_incan(
                bri, transitiontime=int(MIN_BRIDGE_CMD_INTERVAL * 10))
            if elapsed_time >= fade_time:
                break
            time_to_next_step = step_time - ((time() - start_time) % step_time)
            sleep(max(MIN_BRIDGE_CMD_INTERVAL, time_to_next_step))

    def main(self):
        self.fade(self.opts.start_brightness, self.opts.final_brightness,
                  self.opts.fade_time)


def main():
    default_run(IncandescentFadeProgram)
