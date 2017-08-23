#!/usr/bin/env python3

import time

from base import BaseProgram, default_run


class PowerLossRestoreProgram(BaseProgram):
    """A program that tries to keep track of light state and automatically
    restore it when lights return to their default power-on state due to
    power interruption
    """

    def add_light_state_opt(self):
        # Light state restoration does not apply to this program
        return

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.opt_parser.add_argument(
            '-t', '--monitor-time',
            dest='monitor_time', type=self.int_within_range(1, None),
            default=60,
            help='interval to poll for light state in seconds (default: %(default)s)')
        self.opt_parser.add_argument(
            '-i', '--individual-mode',
            dest='individual', action='store_true',
            help='''restore lights individually when reset, rather than restoring only
all lights as a group when they all are in initial power-up state''')

    def run(self):
        states = None

        while True:
            states = self.bridge.collect_light_states(
                self.lights, states, include_default_state=False)
            time.sleep(self.opts.monitor_time)

            if self.opts.individual:
                for light in self.lights:
                    if self.bridge.light_is_in_default_state(light):
                        self.log.info('Restoring light %d', light)
                        self.bridge.restore_light_states([light], states)
            else:
                for light in self.lights:
                    if not self.bridge.light_is_in_default_state(light):
                        break
                else:
                    # Restore state if all monitored lights appear to
                    # have been reset
                    self.log.info('All lights in default state, restoring original state')
                    self.bridge.restore_light_states(self.lights, states)


if __name__ == '__main__':
    default_run(PowerLossRestoreProgram)
