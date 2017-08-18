#!/usr/bin/env python3

import random
import time

from base import (BaseProgram, default_run)
from fading_colors import FadingColorsProgram


class ChasingColorsProgram(FadingColorsProgram):

    def get_description(self):
        return 'Produce a Philips Hue lighting random color chasing effect.'

    def get_usage_epilog(self):
        return '\n\n'.join(
            [self.usage_light_order_msg, self.usage_no_lights_msg,
             self.usage_first_run_msg])

    def _add_opts(self, parser):
        BaseProgram._add_opts(self, parser)

        self._add_cycle_time_opt(parser, default=10)
        self._add_range_parse_opts(parser)

    def run(self):
        self.turn_on_lights()

        while True:
            new_h = random.randint(*self.opts.hue_range)
            new_s = random.randint(*self.opts.sat_range)
            new_b = random.randint(*self.opts.bri_range)
            for L in self.lights:
                ls = self.bridge.get_light(L.light_id)['state']
                save_h, save_s, save_b = ls['hue'], ls['sat'], ls['bri']
                self.bridge.set_light(
                    L.light_id, {'hue': new_h, 'sat': new_s, 'bri': new_b},
                    transitiontime=0)
                new_h, new_s, new_b = save_h, save_s, save_b
            time.sleep(self.opts.cycle_time / 10)


if __name__ == '__main__':
    default_run(ChasingColorsProgram)
