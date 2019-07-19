# Copyright (C) 2017 Travis Evans
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Helper/convenience functions and extensions to the phue.py library
from https://github.com/studioimaginaire/phue
"""

from collections import defaultdict
import logging
import random
import time

# https://github.com/studioimaginaire/phue
from phue import Bridge, is_string, PhueRequestTimeout


MIN = {'bri': 1, 'hue': 0, 'sat': 0, 'xy': 0.0, 'ct': 153, 'ctk': 2000,
       'inc': 1, 'xct': 1, 'xctk': 1}
"""Table of minimum allowed values for light parameters"""

MAX = {'bri': 254, 'hue': 65535, 'sat': 254, 'xy': 1.0, 'ct': 500, 'ctk': 6535,
       'inc': 254, 'xct': int(1e6), 'xctk': int(1e8)}
"""Table of maximum allowed values for light parameters"""

WIDTH = {'bri': (3, 0), 'hue': (5, 0), 'sat': (3, 0), 'xy': (1, 4), 'ct': (3, 0),
         'ctk': (4, 0), 'inc': (3, 0), 'xct': (7, 0), 'xctk': (9, 0)}
"""Table of formatting widths for light parameters in format (number of
integer part digits, number of fractional part digits)
"""

DEFAULT_TRANSITION_TIME = 4
"""Transition time, in deciseconds, used by bridge for lights if one is
not specified
"""

DEFAULT_BRIDGE_RETRIES = 8640
DEFAULT_BRIDGE_RETRY_WAIT = 10
"""Default values of 'retries' and 'retry_wait' arguments to
ExtendedBridge.__init__"""

logger = logging.getLogger(__name__)


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

    return [x, y]


def tungsten_cct(brightness):
    """Return an approximate tungesten color tempearture in Kelvin for an
    incandescent light dimmed to match the given Hue brightness level
    from 1-254.
    """
    return 5.63925392181 * brightness + 1423.98106079


def conv_ct(color_temp):
    """Convert color_temp from mired to Kelvin or vice-versa."""
    return 1000000 / color_temp


def iconv_ct(color_temp):
    """Convert color_temp from mired to Kelvin and truncate to int."""
    return int(conv_ct(color_temp))


def decisleep(deciseconds):
    """Sleep for the given number of deciseconds (seconds/10) using a
    monotonic clock source unaffected by process suspension (e.g.,
    SIGSTOP). time.sleep() (in CPython, at least) would sleep for the
    given time *plus* the total time the process spent suspended. This
    routine instead counts the time suspended toward the sleep interval,
    so that if the process is suspended briefly and then resumed, it
    will still sleep for close to the expected real time (or resume
    immediately upon receiving SIGCONT, if it remained suspended past
    the time the sleep was due to end). Sleep precision is within 0.1
    second.
    """
    start_time = time.monotonic()
    end_time = start_time + deciseconds/10
    while time.monotonic() < end_time:
        time.sleep(.05)


def random_hue():
    """Generate a random light hue parameter value (0-65535), roughly
    weighted so that the result has an equal probability of being chosen
    within a particular named spectral color: red, orange, yellow,
    green, cyan, blue, purple, or magenta
    """
    hue_buckets = [62000-65536, 2000, 6000, 11000, 34000, 44000, 48000, 50000, 62000]
    bucket_idx = random.randint(1, len(hue_buckets) - 1) - 1
    low = hue_buckets[bucket_idx]
    high = hue_buckets[bucket_idx + 1] - 1
    hue_value = random.randint(low, high) % 65536
    return hue_value


class UnsupportedLightModel(Exception):
    pass


class PowerCalculator:
    """Object for calculating power consumption of supported models of Hue
    lights, based on information published at
    <https://developers.meethue.com/energyconsumption>
    """
    def __init__(self):
        self.constants = {
            'LWB014': {
                'type': 'Dimmable light',
                'min_dimlevel': .05,
                'standby_power': .4,
                'max_power': 9,
                'c': -.1484,
                'd': 1.0845,
                'e': .0607,
            },
            'LTW004': {
                'type': 'Color temperature light',
                'min_dimlevel': .01,
                'standby_power': .2,
                'max_power': 10,
                'a': .000164,
                'b': .352,
                'c': -.1484,
                'd': 1.0845,
                'e': .0607,
                'f': -.000115,
                'g': 1.459,
            },
            'LTW011': {
                'type': 'Color temperature light',
                'min_dimlevel': .01,
                'standby_power': .2,
                'max_power': 9,
                'a': .000164,
                'b': .352,
                'c': -.1484,
                'd': 1.0845,
                'e': .0607,
                'f': -.000115,
                'g': 1.459,
            },
            'LCT014': {
                'type': 'Extended color light',
                'min_dimlevel': .01,
                'standby_power': .2,
                'max_power': 10,
                'c': -.1484,
                'd': 1.0845,
                'e': .0607,
                'k0': 1.9738027,
                'k1': .00080357,
                'k2': -.02507075,
                'k3': -.0002499,
                'k4': 8.6021e-05,
                'k5': .00018992,
                'k6': 2.3183e-06,
                'k7': -7.983e-07,
                'k8': -1.786e-08,
                'k9': -7.1209e-07,
                'k10': -5.2436e-09,
                'k11': 1.404e-09,
                'k12': 3.8962e-10,
                'k13': 0,
                'k14': 9.4761e-10,
                'l0': 1,
                'l1': -.00424132,
                'l2': .000528623,
                'l3': .000111131,
                'l4': -6.1015e-05,
                'l5': 1.92599e-05,
                'l6': -8.2638e-07,
                'l7': 5.62658e-08,
                'l8': 1.62112e-07,
                'l9': -1.3746e-07,
                'l10': 1.821e-09,
                'l11': 5.21514e-10,
                'l12': -3.0929e-10,
                'l13': 0,
                'l14': 1.07363e-10,
            },
        }
        self.constants['LCT011'] = self.constants['LCT014']
        self.constants['LCT016'] = self.constants['LCT014']

    def get_constants(self, modelid):
        """Retrieve a dict of light-model-specific constants for calculations"""
        try:
            return self.constants[modelid]
        except KeyError:
            raise UnsupportedLightModel(modelid)

    def dim_level(self, modelid, bri):
        """Return the dimming level (as a percentage) given the brightness
        setting 'bri' for the given light 'modelid' returned from the
        Hue API
        """
        cons = self.get_constants(modelid)
        return cons['min_dimlevel'] + ((1 - cons['min_dimlevel']) * (bri - 1) ** 2) / 253 ** 2

    def power(self, modelid, state):
        """Return the calculated power consumption in watts of light model
        'modelid' given light state mapping 'state' for that light
        """
        cons = self.get_constants(modelid)
        dim_level = self.dim_level(modelid, state['bri'])

        if state['on']:

            if cons['type'] == 'Dimmable light':
                power = (cons['max_power'] *
                         (cons['c'] * dim_level ** 2 + cons['d'] * dim_level + cons['e']))

            elif cons['type'] == 'Color temperature light':
                cct = conv_ct(state['ct'])
                if cct <= 4000:
                    power = cons['max_power'] * (cons['a'] * cct + cons['b']) * (
                        cons['c'] * dim_level ** 2 + cons['d'] * dim_level + cons['e'])
                else:
                    power = cons['max_power'] * (cons['f'] * cct + cons['g']) * (
                        cons['c'] * dim_level ** 2 + cons['d'] * dim_level + cons['e'])

            elif cons['type'] == 'Extended color light':
                hue, sat = state['hue'] / 256, state['sat']
                p_dim = cons['c'] * dim_level ** 2 + cons['d'] * dim_level + cons['e']
                p_flux = (cons['k0'] + cons['k1'] * hue + cons['k2'] * sat + cons['k3'] * hue ** 2 +
                          cons['k4'] * hue * sat + cons['k5'] * sat ** 2 + cons['k6'] * hue ** 3 +
                          cons['k7'] * hue ** 2 * sat + cons['k8'] * hue * sat ** 2 + cons['k9'] *
                          sat ** 3 + cons['k10'] * hue ** 4 + cons['k11'] * hue ** 3 * sat +
                          cons['k12'] * hue ** 2 * sat ** 2 + cons['k13'] * hue * sat ** 3 +
                          cons['k14'] * sat ** 4)
                p_bri = (cons['l0'] + cons['l1'] * hue + cons['l2'] * sat + cons['l3'] * hue ** 2 +
                         cons['l4'] * hue * sat + cons['l5'] * sat ** 2 + cons['l6'] * hue ** 3 +
                         cons['l7'] * hue ** 2 * sat + cons['l8'] * hue * sat ** 2 + cons['l9'] *
                         sat ** 3 + cons['l10'] * hue ** 4 + cons['l11'] * hue ** 3 * sat +
                         cons['l12'] * hue ** 2 * sat ** 2 + cons['l13'] * hue * sat ** 3 +
                         cons['l14'] * sat ** 4)
                power = cons['max_power'] * p_dim * min(p_flux, p_bri)

            else:
                raise AssertionError('Unsupported light type: %s' % cons['type'])

            return power

        else:
            return cons['standby_power']


class BridgeError(Exception):
    """Base exception for Hue bridge errors"""
    pass


class BridgeInternalError(BridgeError):
    """Exception for Hue bridge internal error (usually caused by bridge
    being temporarily too busy with requests
    """
    pass


class ExtendedBridge(Bridge):
    """A phue Bridge object with some extra enhancements and bug
    workarounds

    Additional keyword arguments:

    retries: Number of times to retry if bridge connection error
    occurs (0 means do not retry)

    retry_wait: Number of seconds to wait between retries if bridge
    connection error occurs
    """
    def __init__(self, *args, **kwargs):
        self.retries = kwargs.pop('retries', DEFAULT_BRIDGE_RETRIES)
        self.retry_wait = kwargs.pop('retry_wait', DEFAULT_BRIDGE_RETRY_WAIT)
        Bridge.__init__(self, *args, **kwargs)

        self._cached_light_state = defaultdict(dict)
        self.power_calculator = PowerCalculator()

    def __contains__(self, key):
        """Make syntax like "light_id in bridge" work properly"""
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    @staticmethod
    def _set_light_translate_extensions(params_dict):
        """Transform in place any extended light parameters in params_dict into
        those the superclass set_light() call can understand.
        """
        if 'inc' in params_dict:
            params_dict['bri'] = params_dict['inc']
            # Warning: If this code somehow changes so that
            # tungesten_cct is no longer used to calculate ctk, then
            # lightct_curses.py should be updated as well when it
            # converts 'inc' to extended CT fields for display
            params_dict['ctk'] = tungsten_cct(params_dict.pop('inc'))
        if 'ct' in params_dict:
            if not MIN['ct'] <= params_dict['ct'] <= MAX['ct']:
                params_dict['ctk'] = iconv_ct(params_dict.pop('ct'))
        if 'ctk' in params_dict:
            params_dict['xy'] = kelvin_to_xy(params_dict.pop('ctk'))

    def _set_light_convert_args(self, light_id, parameter, value=None):
        """Canonicalize light_id (which may be a str or int representing a
        single light or a sequence of light IDs) into a sequence and
        parameter/value (which may be either an individual string and
        value, respectively, or a dict stored in parameter) into a
        dict. Translate extended light parameters, then return the
        resulting light_id sequence and parameter dict.
        """
        if isinstance(parameter, dict):
            params = parameter
        else:
            params = {parameter: value}

        light_id_seq = light_id
        if isinstance(light_id, int) or is_string(light_id):
            light_id_seq = [light_id]

        self._set_light_translate_extensions(params)

        return (light_id_seq, params)

    def request(self, *args, **kwargs):
        """A wrapper around phue.Bridge().request that automatically retries
        operations in case of bridge communication failure, instead of
        immediately throwing an exception.
        """
        curr_retries = 0
        while True:
            try:
                return Bridge.request(self, *args, **kwargs)
            except (ConnectionError, OSError, PhueRequestTimeout) as e:
                logger.warning('Bridge connection error: %s', e)
                if curr_retries >= self.retries:
                    logger.error('Retry limit exceeded; giving up')
                    raise e
                else:
                    logger.warning('Retry %d/%d in %ss', curr_retries + 1,
                                   self.retries, self.retry_wait)
                    time.sleep(self.retry_wait)
                    curr_retries += 1

    def api(self, address, body=None, method=None):
        """Make a direct call to the Hue API at given address starting with
        resource name (i.e., without the initial "/api/<username>/" part)
        with optional body (a dict that will be translated to JSON) and
        given HTTP method. The default method is "GET" if body is None,
        else "PUT".
        """
        req_address = '/api/%s/%s' % (self.username, address)
        if method is None:
            method = 'GET' if body is None else 'PUT'
        return self.request(method, req_address, body)

    def set_light(self, light_id, parameter, value=None,
                  transitiontime=None):
        """Extended version of self.set_light with the following enhancements:

        - A 'ctk' parameter that accepts a color temperature in Kelvin
          is supported. This uses an internal formula and will actually
          set the 'xy' colormode as far as the bridge is concerned.

        - The range of 'ct' and 'ctk' is extended. 'ct' values from 40
          to 250 or 'ctk' values from 1000 to 25,000 will work. Values
          outside this range may work reasonably for some applications
          but may not necessarily yield accurate colors. (Note: As a
          side effect, setting a 'ct' value outside the Hue API's
          officially-supported 153–500 mired range will cause the
          light's colormode to be subsequently reported as 'xy' instead
          of 'ct'.)

        - An 'inc' parameter that accepts an int from 1 to 254 is
          supported. It sets the 'bri' parameter to this value, then
          sets the light to a color that simulates the appearance of an
          incandescent lamp dimmed to about that brightness level. This
          parameter conflicts with and should not be used together with
          'bri', 'ct', 'xy', 'hue', or 'sat'.
        """
        light_ids, params = self._set_light_convert_args(
            light_id, parameter, value)

        if params:
            return Bridge.set_light(self, light_ids, params, value=None,
                                    transitiontime=transitiontime)
        return [[]]

    def _set_light_optimize_params(self, light_id, params):
        """Return a copy of set_light params dict with redundant items for the
        given light_id removed
        """
        state = self._cached_light_state[light_id]
        new_params = params.copy()
        for param, value in params.items():

            # Remove some cached parameters if a parameter they're
            # dependent on changes
            if param == 'on' and not value:
                # Erase cached brightness if sending off command
                # because the Hue system often forgets it later, and
                # it then needs to be resent
                state.pop('bri', None)
            elif param in ('hue', 'sat'):
                for p in ('xy', 'ct'):
                    state.pop(p, None)
            elif param == 'xy':
                for p in ('hue', 'sat', 'ct'):
                    state.pop(p, None)
            elif param == 'ct':
                for p in ('hue', 'sat', 'xy'):
                    state.pop(p, None)

            if param in state and value == state[param]:
                # Never consider 'transitiontime'; it's not persistent
                # and should always be sent
                if param != 'transitiontime':
                    new_params.pop(param)

                logger.debug('Removed: %s', param)
            self._cached_light_state[light_id][param] = value
        return new_params

    def set_light_optimized(self, light_id, parameter, value=None,
                            transitiontime=None, clear_cache=False):
        """Same as self.set_light, but remember the light states and avoid
        sending redundant commands to the bridge that would set a light
        attribute to the same as it already is. This can be used to
        reduce load on the bridge and Zigbee network and improve
        responsiveness in the case of sending frequent commands.

        If, between calls to this method, self.set_light is called
        directly, or anything else changes a light's state, the light
        may not be updated correctly. If there is a chance that this has
        happened, clear_cache=True should be passed to reset the
        memorized light states and ensure that the full command is sent
        to the light.
        """
        light_ids, params = self._set_light_convert_args(
            light_id, parameter, value)
        result = []
        logger.debug('Input parms: %s', params)

        if clear_cache:
            self._cached_light_state.clear()

        for light in light_ids:
            if is_string(light):
                converted_light = int(self.get_light_id_by_name(light))
            else:
                converted_light = light

            this_lights_params = self._set_light_optimize_params(
                converted_light, params)
            logger.debug('Output parms for light %s: %s',
                         light, this_lights_params)
            next_result = self.set_light(light, this_lights_params,
                                         transitiontime=transitiontime)[0]
                #                                                      ^^^
                # We always call for one light at a time, so the return
                # list should only contain one item
            result.append(next_result)

        return result

    @staticmethod
    def normalized_light_state(state):
        """Return a canonocalized copy of a light state dictionary (e.g., from
        phue.Bridge.get_light()) so that it can be safely passed to
        phue.Bridge.set_light()'s parameter list to restore the light to its
        original state.

        Experimentally, it seems that this may not really be necessary, but
        just in case.…
        """
        new_state = state.copy()

        # Apparently a new and undocumented attribute 'mode' recently
        # appeared which the bridge doesn't like to modify. So ignore it
        # for now (at least until it's known what it's for)
        new_state.pop('mode', None)

        if 'colormode' in state:
            if state['colormode'] == 'hs':
                for k in ('ct', 'xy'):
                    new_state.pop(k, None)
            elif state['colormode'] == 'ct':
                for k in ('hue', 'sat', 'xy'):
                    new_state.pop(k, None)
            elif state['colormode'] == 'xy':
                for k in ('ct', 'hue', 'sat'):
                    new_state.pop(k, None)

        for k in ('colormode', 'reachable'):
            new_state.pop(k, None)

        return new_state

    @staticmethod
    def sanitized_light_state(state):
        """Return a version of light state 'state' (e.g., from self.get_light())
        that has parameters normalized to values within valid ranges
        """
        state = state.copy()
        for key in MIN:
            if key in state:
                value = state[key]
                if key == 'xy':
                    state[key] = [min(max(MIN[key], x), MAX[key]) for x in state[key]]
                else:
                    state[key] = min(max(MIN[key], value), MAX[key])
        return state

    @staticmethod
    def light_state_is_default(state):
        """Return whether the given light state dictionary contains parameters
        that match the Hue lamps' power-on defaults.
        """
        return (state['reachable']
                and state['on']
                and state.get('colormode', 'ct') == 'ct'
                and state.get('ct', 366) == 366
                and state.get('bri', None) == 254
        )

    def collect_light_states(self, light_ids, state=None,
                             include_default_state=True):
        """Collect a state dict for each light in given sequence of light
        IDs/names. If include_default_state, this will include the state
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

        for light in light_ids:
            light_state = self.get_light(light)['state']
            if light_state['reachable']:
                if (not self.light_state_is_default(light_state)
                        or include_default_state):
                    state[light] = light_state
                else:
                    logger.info('Light %d in default state, not saving state',
                                light)
            else:
                if light not in state:
                    logger.info('Light %d is unreachable; recording last known state',
                                light)
                    state[light] = light_state
                else:
                    logger.info('Light %d is unreachable; temporarily skipping new state save',
                                light)
        return state

    def restore_light_states(self, light_ids, state, transitiontime=4):
        """Set the state of all lights represented in the sequence of light IDs
        to that specified in the state dict (such as that returned by
        self.collect_light_states). transitiontime is the light state
        transition time in deciseconds to send to the Hue API.
        """
        for light in light_ids:
            try:
                light_state = state[light]
            except KeyError:
                logger.info("Could not restore state of light %d because this"
                            " light's state was not known", light)
            else:
                results = self.set_light(
                    light, self.normalized_light_state(light_state),
                    transitiontime=transitiontime)
                for result in results[0]:
                    if ('error' in result and
                            result['error']['type'] == 901):
                        raise BridgeInternalError

    def light_is_in_default_state(self, light_id):
        """Return whether the given light with ID or name light_id is currently
        on, reachable, and at its default power-on state.
        """
        state = self.get_light(light_id)['state']
        return self.light_state_is_default(state)

    def get_light_power(self, light_id):
        """Retrieve calculated power consumption of light in watts if model is
        supported, else raise UnsupportedLightModel
        """
        light_data = self.get_light(light_id)
        return self.power_calculator.power(light_data['modelid'], light_data['state'])
