#!/usr/bin/env python3

from random import randint
import threading
import time

from base import (BaseProgram, default_run)


class CFLSimulationProgram(BaseProgram):
    """Simulate certain types of compact fluorescent lamps with their
    power-on warm-up behaviors
    """

    def __init__(self, raw_arguments=None):
        BaseProgram.__init__(self, raw_arguments)
        self.bridge_lock = threading.Lock()

    def add_keep_state_opt(self):
        """Make default option to *not* restore state since the primary purpose
        of the program is to mimic the power-on and subsequent
        stabilization of another light source
        """
        self.opt_parser.add_argument(
            '--restore-lights',
            dest='keep_light_state', action='store_false',
            help='return lights to their original state on exit')

    def simulate(self, light_id):
        """Run the simulation for one light given by light_id"""
        stages = [{'on': True, 'transitiontime': 0}]
        have_pink_stage = randint(0, 1)
        if have_pink_stage:
            init_sat = randint(25, 90)
            init_bri = randint(1, 40)
            stages.append({'bri': init_bri,
                           'sat': init_sat,
                           'hue': 60000,
                           'transitiontime': 0})
            settle_sat = randint(init_sat, 90)
            settle_bri = randint(1, init_bri)
            stages.append({'bri': settle_bri,
                           'sat': settle_sat,
                           'transitiontime': randint(50, 150)})
            stages.append({'bri': randint(50, 70),
                           'ct': 286,
                           'transitiontime': randint(50, 350)})
            stages.append({'bri': 254,
                           'transitiontime': randint(600, 1200)})
        else:
            stages.append({'bri': randint(1, 40),
                           'ct': randint(286, 315),
                           'transitiontime': 0})
            stages.append({'bri': 254,
                           'transitiontime': randint(800, 1600)})

        for stage in stages:
            with self.bridge_lock:
                self.bridge.set_light(light_id, stage)
            time.sleep(stage.get('transitiontime', 40) / 10 + .1)

    def main(self):
        threads = []
        for light in self.lights:
            thread = threading.Thread(
                target=self.simulate, args=(light,), daemon=True)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()


if __name__ == '__main__':
    default_run(CFLSimulationProgram)
