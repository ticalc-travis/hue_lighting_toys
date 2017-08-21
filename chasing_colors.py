#!/usr/bin/env python3

import random
import time

from base import (BaseProgram, default_run)
from fading_colors import FadingColorsProgram
from phue_helper import normalize_light_state


class ChasingColorsProgram(FadingColorsProgram):
    """Produce a Philips Hue lighting random color chasing effect"""

    def get_usage_epilog(self):
        return '\n\n'.join(
            [self.usage_light_order_msg, self.usage_no_lights_msg,
             self.usage_first_run_msg])

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.add_cycle_time_opt(default=10)
        self.add_range_parse_opts()

    def main(self):
        self.turn_on_lights()

        # Get light states from bridge once and then keep track of them
        # ourself thereafter to reduce bridge requests and avoid weird
        # effects due to network/state update delays
        light_state = self.bridge.collect_light_states(self.lights)

        while True:
            new_state = {'hue': random.randint(*self.opts.hue_range),
                         'sat': random.randint(*self.opts.sat_range),
                         'bri': random.randint(*self.opts.bri_range)}
            for light in self.lights:
                orig_state = light_state[light]
                self.bridge.set_light(light,
                                      normalize_light_state(new_state),
                                      transitiontime=0)
                light_state[light] = new_state
                new_state = orig_state
            time.sleep(self.opts.cycle_time / 10)


if __name__ == '__main__':
    default_run(ChasingColorsProgram)
