"""Helper/convenience functions and extensions to the phue.py library
from https://github.com/studioimaginaire/phue
"""

import logging
from time import sleep

from phue import Bridge       # https://github.com/studioimaginaire/phue

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
    """

    def __contains__(self, key):
        """Make syntax like "light_id in bridge" work properly"""
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    @staticmethod
    def normalize_light_state(state):
        """Return a canonocalized copy of a light state dictionary (e.g., from
        phue.Bridge.get_light()) so that it can be safely passed to
        phue.Bridge.set_light()'s parameter list to restore the light to its
        original state.

        Experimentally, it seems that this may not really be necessary, but
        just in case.…
        """
        new_state = state.copy()

        if 'on' in state and not state['on']:
            for k in ('alert', 'bri', 'ct', 'effect', 'hue', 'sat', 'xy'):
                new_state.pop(k, None)
        elif 'colormode' in state:
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
    def light_state_is_default(state):
        """Return whether the given light state dictionary contains parameters
        that match the Hue lamps' power-on defaults.
        """
        return (state['reachable']
                and state['on']
                and state['colormode'] == 'ct'
                and state['bri'] == 254
                and state['ct'] == 366)

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

    def restore_light_states(self, light_ids, state,
                             transitiontime=4):
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
                    light, self.normalize_light_state(light_state),
                    transitiontime=transitiontime)
                for result in results[0]:
                    if ('error' in result and
                            result['error']['type'] == 901):
                        raise BridgeInternalError

    def restore_light_states_retry(
            self, max_retries, retry_wait, light_ids, state,
            transitiontime=4):
        """Try to call restore_light_states; if bridge returns a temporary
        error, try again up to max_retries times, waiting retry_wait
        seconds between each try
        """

        # Make at least one attempt (retries + 1)
        for _ in range(max(max_retries + 1, 1)):
            try:
                self.restore_light_states(light_ids, state, transitiontime)
            except BridgeInternalError:
                logger.warning('Bridge command failure; retrying…')
                sleep(retry_wait)
            else:
                break
        else:
            logger.warning('Retry limit exceeded; giving up')

    def light_is_in_default_state(self, light_id):
        """Return whether the given light with ID or name light_id is currently
        on, reachable, and at its default power-on state.
        """
        state = self.get_light(light_id)['state']
        return self.light_state_is_default(state)
