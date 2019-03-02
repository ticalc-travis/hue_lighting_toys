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

from random import choice, randint, normalvariate
import threading
import time

from hue_toys.base import BaseProgram, default_run
from hue_toys.chasing_colors import ChasingColorsProgram
from hue_toys.phue_helper import MIN, MAX, decisleep

# Average and standard deviation of on/off times to use in deciseconds
DEFAULT_ON_TIME_AVG = 8
DEFAULT_ON_TIME_SD = 3
DEFAULT_OFF_TIME_AVG = 13
DEFAULT_OFF_TIME_SD = 6


class FlashingColorsProgram(ChasingColorsProgram):
    """Flash lights on and off with different colors"""

    def __init__(self, *args, **kwargs):
        ChasingColorsProgram.__init__(self, *args, **kwargs)

        self.bridge_lock = threading.Lock()

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.add_range_parse_opts()

        self.opt_parser.add_argument(
            '-navg', '--on-time-avg',
            type=self.int_within_range(0, None),
            metavar='DECISECONDS', default=DEFAULT_ON_TIME_AVG,
            help='average “on” time per flash in tenths of a second (default: %(default)s)')
        self.opt_parser.add_argument(
            '-nsd', '--on-time-sd',
            type=self.int_within_range(0, None),
            metavar='DECISECONDS', default=DEFAULT_ON_TIME_SD,
            help='standard deviation of “on” time per flash in tenths of a second (default: %(default)s)')
        self.opt_parser.add_argument(
            '-favg', '--off-time-avg',
            type=self.int_within_range(0, None),
            metavar='DECISECONDS', default=DEFAULT_OFF_TIME_AVG,
            help='average “off” time per flash in tenths of a second (default: %(default)s)')
        self.opt_parser.add_argument(
            '-fsd', '--off-time-sd',
            type=self.int_within_range(0, None),
            metavar='DECISECONDS', default=DEFAULT_OFF_TIME_SD,
            help='standard deviation of “off” time per flash in tenths of a second (default: %(default)s)')

        self.add_power_fail_opt()

    def get_usage_epilog(self):
        # Use generic epilog; don't display info about sequencing order
        # like chasing_colors does since it's not applicable to this
        # program
        return BaseProgram.get_usage_epilog(self)

    def set_light(self, *args, **kwargs):
        """Wrapper for bridge set_light method, using proper locking for thread
        safety
        """
        with self.bridge_lock:
            self.bridge.set_light(*args, **kwargs)

    def do_light_flash(self, light_id):
        """Flash the light with id “light_id” different colors"""
        while True:
            params = self.get_random_parms()
            params['on'] = True
            self.set_light(light_id, params, transitiontime=0)
            decisleep(normalvariate(self.opts.on_time_avg, self.opts.on_time_sd))
            self.set_light(light_id, 'on', False, transitiontime=0)
            decisleep(normalvariate(self.opts.off_time_avg, self.opts.off_time_sd))

    def main(self):
        threads = []
        for light in self.lights:
            thread = threading.Thread(
                target=self.do_light_flash, args=(light,), daemon=True)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()


def main():
    default_run(FlashingColorsProgram)
