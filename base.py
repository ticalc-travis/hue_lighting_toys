#!/usr/bin/env python3

"""Base classes and helper functions for programs dealing with Philips
Hue smart lights
"""

import argparse
import signal
import sys
import textwrap

import phue                     # https://github.com/studioimaginaire/phue


def kelvin_to_xy(kelvin):
    """Return an approximate CIE [x,y] color value for the given kelvin
    color temperature. Should work reasonably from 1000K to 15,000K.
    """

    # Formula from Wikipedia
    # https://en.wikipedia.org/wiki/Planckian_locus
    #
    # This actually uses the formula given for CIE 1960 UCS, then
    # converts the result to CIE 1931, used by the Philips Hue
    # lights. This provides a lower limit than the formula they give for
    # doing the approximation directly in CIE 1931, which is only
    # accurate down to 1667K.

    # Calculate CIE 1960 coordinates
    u = ((.860117757 + 1.54118254e-4 * kelvin + 1.28641212e-7 * kelvin**2)
         / (1 + 8.42420235e-4 * kelvin + 7.08145163e-7 * kelvin**2))
    v = ((.317398726 + 4.22806245e-5 * kelvin + 4.20481691e-8 * kelvin**2)
         / (1 - 2.89741816e-5 * kelvin + 1.61456053e-7 * kelvin**2))

    # Convert to CIE 1931
    x = (3*u) / (2*u - 8*v + 4)
    y = (2*v) / (2*u - 8*v + 4)

    return [x,y]


def tungsten_cct(brightness):
    """Return an approximate tungesten color tempearture in Kelvin for an
    incandescent light dimmed to match the given Hue brightness level
    from 1-254.
    """
    return 5.63925392181 * brightness + 1423.98106079


def normalize_light_state(state):
    """Return a canonocalized copy of a light state dictionary (e.g., from
    phue.Bridge.get_light()) so that it can be safely passed to
    phue.Bridge.set_light()'s parameter list to restore the light to its
    original state.

    Experimentally, it seems that this may not really be necessary, but
    just in case.…
    """
    new_state = state.copy()

    if not state['on']:
        [new_state.pop(k) for k in ('alert', 'bri', 'ct', 'effect', 'hue',
                                    'sat', 'xy')]
    elif state['colormode'] == 'hs':
        [new_state.pop(k) for k in ('ct', 'xy')]
    elif state['colormode'] == 'ct':
        [new_state.pop(k) for k in ('hue', 'sat', 'xy')]
    elif state['colormode'] == 'xy':
        [new_state.pop(k) for k in ('ct', 'hue', 'sat')]

    [new_state.pop(k) for k in ('colormode', 'reachable')]
    return new_state


def light_state_is_default(state):
    """Return whether the given light state dictionary contains parameters
    that match the Hue lamps' power-on defaults.
    """
    return (state['reachable']
            and state['on']
            and state['colormode'] == 'ct'
            and state['bri'] == 254
            and state['ct'] == 366)


class ProgramArgumentError(Exception):
    """Exception signaling incorrect command-line arguments that prevent
    program execution
    """
    pass


class BaseProgram():
    """A sample CLI program for the Philips Hue system that takes
    command-line arguments and connects to the given bridge and operates
    on the specified lights
    """

    usage_first_run_msg = '''The first time this script is run on a device, it may be necessary to
press the button on the bridge before running the script so that it can
be registered to access the bridge and lighting system.'''

    usage_light_order_msg = '''Lights will be sequenced in the order specified.'''

    usage_no_lights_msg = '''If no lights are specified, all lights found on the bridge will be
used in the effect.'''

    def __init__(self, raw_arguments=None):
        """Parse raw arguments and initialize connection to Hue bridge"""
        self.init_arg_parser()
        self.opts = self.opt_parser.parse_args(raw_arguments)

        self.bridge = self.get_bridge()
        self.lights = self.get_lights()
        if not self.lights:
            raise ProgramArgumentError('No lights available')

    def get_description(self):
        """Get formatted program description"""
        return textwrap.fill(self.__doc__)

    def get_usage_epilog(self):
        """Construct and return program epilogue for usage message"""
        return '\n\n'.join(
            [self.usage_no_lights_msg, self.usage_first_run_msg])

    def add_bridge_opts(self):
        """Add generic bridge arguments to argument parser"""
        self.opt_parser.add_argument(
            '-b', '--bridge',
            dest='bridge_address',
            help='Hue bridge IP or hostname')
        self.opt_parser.add_argument(
            '-bu', '--bridge-username',
            dest='bridge_username',
            help='Hue bridge username')
        self.opt_parser.add_argument(
            '-bc', '--bridge-config',
            dest='bridge_config',
            help='path of config file for bridge connection parameters')

    def add_light_opts(self):
        """Add generic light-listing arguments to argument parser"""
        self.opt_parser.add_argument(
            '-ln', '--light-number',
            dest='lights', action='append', type=int, metavar='LIGHT-NUM',
            nargs='+',
            help='use light(s) numbered %(metavar)s')
        self.opt_parser.add_argument(
            '-l', '--light-name',
            dest='lights', action='append', type=str,
            metavar='LIGHT-NAME', nargs='+',
            help='use light(s) named %(metavar)s')

    def add_opts(self):
        """Add program's command arguments to argument parser"""
        self.add_bridge_opts()
        self.add_light_opts()

    def init_arg_parser(self):
        """Set up the command argument parser"""
        self.opt_parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=self.get_description(),
            epilog=self.get_usage_epilog())
        self.add_opts()

    def get_bridge(self):
        """Establish and return a phue Bridge object to use"""
        return phue.Bridge(ip=self.opts.bridge_address,
                           username=self.opts.bridge_username,
                           config_file_path=self.opts.bridge_config)

    def get_lights(self):
        """Find and return a list of light objects representing the lights
        specified by the user, in the order specified
        """
        if self.opts.lights:
            lights = []
            for light in [light for sublist in self.opts.lights
                          for light in sublist]:
                try:
                    lights.append(self.bridge[light])
                except KeyError:
                    print("Warning: No such light: %s" %
                          repr(light), file=sys.stderr)
        else:
            lights = self.bridge.get_light_objects()
        return lights

    def turn_on_lights(self):
        """Turn on all lights to be used"""
        for light in self.lights:
            self.bridge.set_light(light.light_id, 'on', True)

    def collect_light_states(self, light_objs, state=None,
                             include_default_state=True):
        """Collect a state dict for each item in given sequence of Light
        objects. If include_default_state, this will include the state
        of lights that are currently in the default power-on
        state. 'state' is a state dict returned by a previous
        invocation; it can be passed to update the existing data, i.e.,
        in cases where the state of some lights was previously collected
        but could not be obtained this time around (they were
        unreachable, in default state with include_default_state=False,
        etc.), the existing data will be left alone.
        """
        if state is None:
            state = {}

        for light in light_objs:
            light_state = self.bridge.get_light(light.light_id)['state']
            if light_state['reachable']:
                if (not light_state_is_default(light_state)
                        or include_default_state):
                    state[light.light_id] = light_state
                else:
                    print('Light %d in default state, not saving state'
                          % light.light_id)
            else:
                if light.light_id not in light_state:
                    print('Light %d is unreachable; recording last known state'
                          % light.light_id)
                    state[light.light_id] = light_state
                else:
                    print('Light %d is unreachable; temporarily skipping new state save'
                          % light.light_id)
        return state

    def restore_light_states(self, light_objs, state):
        """Set the state of all lights in the sequence of Light objects to that
        specified in the state dict (such as that returned by
        self.collect_light_states)
        """
        for light in light_objs:
            try:
                light_state = state[light.light_id]
            except KeyError:
                print("Could not restore state of light %d because this"
                      " light's state was not known" % light.light_id)
            else:
                self.bridge.set_light(light.light_id,
                                      normalize_light_state(light_state))

    def run(self):
        """Start the program"""
        print('The following lights were specified:')
        for light in self.lights:
            print(light.name)
        print('\nThe lights will now be turned on.')
        self.turn_on_lights()
        print('\nDone!')


def run_with_quit_handler(program):
    """Run a program that catches KeyboardInterrupt and then terminates with
    the appropriate return code on *nix
    """
    try:
        program.run()
    except KeyboardInterrupt:
        sys.exit(signal.SIGINT + 128)    # Terminate quietly on ^C

def default_run(prog_class):
    """Create an instance of prog_class, displaying command argument errors
    if they occur, and supply a return code for this condition or keyboard
    interrupts.
    """
    try:
        prog = prog_class()
    except ProgramArgumentError as e:
        print('Error: %s' % e, file=sys.stderr)
        sys.exit(2)
    else:
        run_with_quit_handler(prog)


if __name__ == '__main__':
    default_run(BaseProgram)
