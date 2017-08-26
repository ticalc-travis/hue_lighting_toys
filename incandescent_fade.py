#!/usr/bin/env python3

from math import copysign
from time import time, sleep

from base import BaseProgram, default_run
from phue_helper import MIN, MAX


MIN_BRIDGE_CMD_INTERVAL = .3
"""Minimum number of seconds between commands sent to bridge"""


class IncandescentFadeProgram(BaseProgram):
    """Simulate an incandescent dimmer fade"""

    def add_light_state_opt(self):
        self.add_restore_opt()

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.opt_parser.add_argument(
            'start_brightness', type=self.int_within_range(MIN['incan'], MAX['incan']),
            help='the starting brightness level (%d–%d); 0 is off' % (
                MIN['incan'], MAX['incan']))
        self.opt_parser.add_argument(
            'final_brightness', type=self.int_within_range(MIN['incan'], MAX['incan']),
            help='the ending brightness level (%d–%d); 0 is off' % (
                MIN['incan'], MAX['incan']))
        self.opt_parser.add_argument(
            'fade_time', type=self.positive_float(),
            help='number of seconds to perform the fade')

    def _set_light_incan(self, level, transitiontime):
        """Set lights to the given brightness of “incandescent bulb” color, or
        turn them off if brightness level is 0.
        """
        if level:
            cmd = {'on': True, 'incan': level}
        else:
            cmd = {'on': False}
        self.bridge.set_light_optimized(self.lights, cmd,
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


if __name__ == '__main__':
    default_run(IncandescentFadeProgram)
