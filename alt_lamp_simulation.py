#!/usr/bin/env python3

from random import choice, randint, normalvariate
import threading
import time

from base import (BaseProgram, default_run)


class LampSimulationProgram(BaseProgram):
    """Simulate certain types of non-LED lamps with their power-on warm-up
    behaviors
    """

    def __init__(self, *args, **kwargs):
        self.models = {'cfl_3500k': self.simulate_3500k,
                       'cfl_2700k': self.simulate_2700k,
                       'sbm': self.simulate_sbm,
        }
        self.default_model_seq = ['cfl_3500k']

        BaseProgram.__init__(self, *args, **kwargs)

        self.bridge_lock = threading.Lock()

    def add_light_state_opt(self):
        self.add_restore_opt()

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.opt_parser.add_argument(
            '-m', '--model',
            dest='models', action='append', default=None,
            choices=sorted(self.models.keys()),
            help='light model to simulate; if specified multiple times, a randomly-chosen model out of the ones specified will be selected for each light')
        self.opt_parser.add_argument(
            '-w', '--warmup-type',
            dest='warmup_type', choices=('deep', 'shallow', 'random'),
            default='random',
            help='variation of warmup to simulate; only applies to CFL simulation models (default: random)')
        self.opt_parser.add_argument(
            '-t', '--time-rate',
            dest='time_rate', type=self.positive_float(), default=1.0,
            help='time rate of simulation (e.g., 2 = double speed, 0.5 = half speed) (default: 1.0)')

    def run_stages(self, stages, light_id):
        """Send a sequence of light commands (parameter dicts to send to
        phue[_helper].Bridge.set_light()), waiting for each transition
        to complete before sending the next one
        """
        for stage in stages:
            stage = stage.copy()
            real_trans_time = round(
                stage.get('transitiontime', 40) * (1 / self.opts.time_rate))
            stage['transitiontime'] = real_trans_time
            with self.bridge_lock:
                self.bridge.set_light(light_id, stage)
            time.sleep(real_trans_time / 10)

    def simulate_2700k(self, light_id):
        """Run a 2700K CFL simulation using the given light_id"""
        stages = [{'on': True, 'transitiontime': 0}]
        if self.opts.warmup_type == 'random':
            deep_warmup = randint(0, 1)
        else:
            deep_warmup = True if self.opts.warmup_type == 'deep' else False
        if deep_warmup:
            stages.append({'bri': randint(1, 40),
                           'hue': randint(57500, 61500),
                           'sat': 130,
                           'transitiontime': 0})

            stages.append({'bri': randint(1, 20),
                           'sat': randint(90, 130),
                           'transitiontime': randint(5, 100)})

            stages.append({'bri': randint(40, 70),
                           'hue': randint(7500, 8500),
                           'sat': 160,
                           'transitiontime': randint(150, 350)})

            stages.append({'bri': 254,
                           'transitiontime': randint(1200, 3200)})

        else:
            stages.append({'bri': randint(20, 60),
                           'hue': randint(7500, 8500),
                           'sat': 160,
                           'transitiontime': 0})

            stages.append({'bri': 254,
                           'transitiontime': randint(1000, 2000)})

        self.run_stages(stages, light_id)

    def simulate_3500k(self, light_id):
        """Run a 3500K CFL simulation using the given light_id"""
        stages = [{'on': True, 'transitiontime': 0}]
        if self.opts.warmup_type == 'random':
            deep_warmup = randint(0, 1)
        else:
            deep_warmup = True if self.opts.warmup_type == 'deep' else False
        if deep_warmup:
            init_bri = randint(1, 40)
            init_sat = randint(25, 90)
            stages.append({'bri': init_bri,
                           'sat': init_sat,
                           'hue': 60000,
                           'transitiontime': 0})

            settle_bri = randint(1, init_bri)
            settle_sat = randint(init_sat, 90)
            stages.append({'bri': settle_bri,
                           'sat': settle_sat,
                           'transitiontime': randint(1, 100)})

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

        self.run_stages(stages, light_id)

    def simulate_sbm(self, light_id):
        """Run a self-ballasted mercury lamp simulation using the given light_id"""
        stages = []

        stages.append({'on': True,
                       'bri': 254,
                       'ctk': 2600,
                       'transitiontime': 0})

        stages.append({'transitiontime': randint(175, 225)})

        stages.append({'bri': int(min(254, normalvariate(224, 30))),
                       'transitiontime': randint(0, 5)})

        stages.append({'bri': 254,
                       'ctk': randint(2600, 2800),
                       'transitiontime': 0})

        stages.append({'ctk': 3500,
                       'transitiontime': randint(400, 700)})

        stages.append({'hue': 6000,
                       'sat': 29,
                       'transitiontime': randint(500, 800)})

        self.run_stages(stages, light_id)

    def main(self):
        threads = []
        if self.opts.models is not None:
            models = self.opts.models
        else:
            models = self.default_model_seq
        for light in self.lights:
            thread = threading.Thread(
                target=self.models[choice(models)], args=(light,), daemon=True)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()


if __name__ == '__main__':
    default_run(LampSimulationProgram)
