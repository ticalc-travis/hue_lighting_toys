#!/usr/bin/env python3

import random
import time

from base import (BaseProgram, default_run)
from fading_colors import FadingColorsProgram


class ChasingColorsProgram(FadingColorsProgram):

    description = '''Produce a Philips Hue lighting random color chasing effect'''

    def get_usage_epilog(self):
        return '\n\n'.join(
            [self.usage_light_order_msg, self.usage_no_lights_msg,
             self.usage_first_run_msg])

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.add_cycle_time_opt(default=10)
        self.add_range_parse_opts()

    def run(self):
        self.turn_on_lights()

        while True:
            new_hue = random.randint(*self.opts.hue_range)
            new_sat = random.randint(*self.opts.sat_range)
            new_bri = random.randint(*self.opts.bri_range)
            for light in self.lights:
                light_state = self.bridge.get_light(light.light_id)['state']
                save_hue = light_state['hue']
                save_sat = light_state['sat']
                save_bri = light_state['bri']
                self.bridge.set_light(
                    light.light_id, {'hue': new_hue,
                                     'sat': new_sat,
                                     'bri': new_bri},
                    transitiontime=0)
                new_hue, new_sat, new_bri = save_hue, save_sat, save_bri
            time.sleep(self.opts.cycle_time / 10)


if __name__ == '__main__':
    default_run(ChasingColorsProgram)
