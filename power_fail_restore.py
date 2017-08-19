#!/usr/bin/env python3

import time

from base import BaseProgram, default_run, light_state_is_default


class PowerLossRestoreProgram(BaseProgram):
    """A program that tries to keep track of light state and automatically
    restore it when lights return to their default power-on state due to
    power interruption
    """

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.opt_parser.add_argument(
            '-t', '--monitor-time',
            dest='monitor_time', type=int, default=60,
            help='interval to poll for light state in seconds (default: %(default)s)')
        self.opt_parser.add_argument(
            '-i', '--individual-mode',
            dest='individual', action='store_true',
            help='''restore lights individually when reset, rather than restoring only
all lights as a group when they all are in initial power-up state''')

    def run(self):
        states = None

        while True:
            states = self.collect_light_states(
                self.lights, states, include_default_state=False)
            time.sleep(self.opts.monitor_time)

            if self.opts.individual:
                for light in self.lights:
                    light_state = self.bridge.get_light(
                        light.light_id)['state']
                    if light_state_is_default(light_state):
                        print('Restoring light %d' % light.light_id)
                        self.restore_light_states([light], states)
            else:
                for light in self.lights:
                    light_state = self.bridge.get_light(
                        light.light_id)['state']
                    if not light_state_is_default(light_state):
                        break
                else:
                    # Restore state if all monitored lights appear to
                    # have been reset
                    print('All lights in default state, restoring original state')
                    self.restore_light_states(self.lights, states)


if __name__ == '__main__':
    default_run(PowerLossRestoreProgram)
