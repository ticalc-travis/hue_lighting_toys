#!/usr/bin/env python3

from random import randint
import threading
import time

from base import (BaseProgram, default_run)


class CFLSimulationProgram(BaseProgram):
    """Simulate certain types of compact fluorescent lamps with their
    power-on warm-up behaviors
    """

    def __init__(self, *args, **kwargs):
        self.models = {'15w_3500k': self.simulate_15w_3500k,
                       '20w_2700k': self.simulate_20w_2700k,
        }
        self.default_model = '15w_3500k'

        BaseProgram.__init__(self, *args, **kwargs)

        self.bridge_lock = threading.Lock()

    def add_light_state_opt(self):
        self.add_restore_opt()

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.opt_parser.add_argument(
            '-m', '--model',
            dest='model', choices=sorted(self.models.keys()),
            default=self.default_model,
            help='light model to simulate')

    def simulate_20w_2700k(self, light_id):
        """Run the simulation for one light given by light_id"""
        stages = [{'on': True, 'transitiontime': 0}]
        have_pink_stage = randint(0, 1)
        if have_pink_stage:
            init_sat = 130
            init_bri = randint(1, 50)
            init_hue = randint(1000, 5000)
            stages.append({'bri': init_bri,
                           'sat': init_sat,
                           'hue': init_hue,
                           'transitiontime': 0})
            settle_sat = randint(90, 130)
            settle_bri = randint(1, 10)
            stages.append({'bri': settle_bri,
                           'sat': settle_sat,
                           'transitiontime': randint(50, 150)})
            stages.append({'bri': randint(40, 70),
                           'hue': randint(7500, 8500),
                           'sat': 132,
                           'transitiontime': randint(150, 350)})
            stages.append({'bri': 254,
                           'transitiontime': randint(1200, 3200)})
        else:
            stages.append({'bri': randint(20, 60),
                           'hue': randint(7500, 8500),
                           'sat': 132,
                           'transitiontime': 0})
            stages.append({'bri': 254,
                           'transitiontime': randint(1000, 2000)})

        for stage in stages:
            with self.bridge_lock:
                self.bridge.set_light(light_id, stage)
            time.sleep(stage.get('transitiontime', 40) / 10 + .1)

    def simulate_15w_3500k(self, light_id):
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
        model_method = self.models[self.opts.model]
        threads = []
        for light in self.lights:
            thread = threading.Thread(
                target=model_method, args=(light,), daemon=True)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()


if __name__ == '__main__':
    default_run(CFLSimulationProgram)
