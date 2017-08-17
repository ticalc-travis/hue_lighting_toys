#!/usr/bin/env python3

import argparse
import signal
import sys
import time

import phue                     # https://github.com/studioimaginaire/phue

def get_bridge(args):
    return phue.Bridge(args.bridge_address)

def is_in_default_state(state):
    return (state['reachable'] and state['on'] and state['colormode'] == 'ct' and
            state['bri'] == 254 and state['ct'] == 366)

def get_lights(bridge, args):
    if args.lights:
        lights = []
        for ll in args.lights:
            for li in ll:
                try:
                    lights.append(bridge[li])
                except KeyError:
                    print("Warning: No such light: %s" % repr(li), file=sys.stderr)
    else:
        lights = bridge.get_light_objects()
    return lights

def get_light_state(bridge, lights, state=None):
    """Collect state for given lights, filling in any missing info"""
    if state is None:
        state = {}
    for L in lights:
        ls = bridge.get_light(L.light_id)['state']
        if ls['reachable']:
            if not is_in_default_state(ls):
                state[L.light_id] = ls
            else:
                print('Light %d in default state, not saving state' % L.light_id)
        else:
            if L.light_id not in state:
                print('Light %d is unreachable; recording last known state' %
                      L.light_id)
                state[L.light_id] = ls
            else:
                print('Light %d is unreachable; temporarily skipping new state save' %
                      L.light_id)
    return state

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
        [new_state.pop(k) for k in ('alert', 'bri', 'ct', 'effect', 'hue', 'sat',
                                    'xy')]
    elif state['colormode'] == 'hs':
        [new_state.pop(k) for k in ('ct', 'xy')]
    elif state['colormode'] == 'ct':
        [new_state.pop(k) for k in ('hue', 'sat', 'xy')]
    elif state['colormode'] == 'xy':
        [new_state.pop(k) for k in ('ct', 'hue', 'sat')]

    [new_state.pop(k) for k in ('colormode', 'reachable')]
    return new_state

def set_light_state(bridge, lights, state):
    for L in lights:
        try:
            s = state[L.light_id]
        except KeyError:
            print("Could not restore state of light %d because this light's state "
                  "was not known" % L.light_id)
        else:
            bridge.set_light(L.light_id, normalize_light_state(s))

def do_monitor(bridge, args, lights):
    state = {}
    while True:
        state = get_light_state(bridge, lights, state)
        time.sleep(args.interval)

        if args.individual:
            for L in lights:
                ls = bridge.get_light(L.light_id)['state']
                if is_in_default_state(ls):
                    print('Restoring light %d' % L.light_id)
                    set_light_state(bridge, [L], state)
        else:
            for L in lights:
                ls = bridge.get_light(L.light_id)['state']
                if not is_in_default_state(ls):
                    break
            else:
                # Restore state if all monitored light appear to have been reset
                print('All lights in default state, restoring original state')
                set_light_state(bridge, lights, state)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Try to detect light reset condition by power loss and then restore the previous light parameters.',
        epilog='If no lights are specified to be used, all lights found on the '
        'bridge will be used. '
        'The first time this script is run on a device, it may be necessary to '
        'press the button on the bridge before running the script so that it can '
        'be authenticated and be permitted to access the bridge and lighting '
        'system.')
    parser.add_argument(
        '-ln', '--light-number',
        dest='lights', action='append', type=int, metavar='LIGHT-NUM', nargs='+',
        help='include light number %(metavar)s in monitoring')
    parser.add_argument(
        '-l', '--light-name',
        dest='lights', action='append', type=str, metavar='LIGHT-NAME', nargs='+',
        help='include light named %(metavar)s in monitoring')
    parser.add_argument(
        '-b', '--bridge',
        dest='bridge_address',
        help='IP address or hostname of the Hue bridge to connect to')
    parser.add_argument(
        '-t', '--monitor-time',
        dest='interval', type=int, default=60,
        help='interval to poll for light state in seconds')
    parser.add_argument(
        '-i', '--individual-mode',
        dest='individual', action='store_true',
        help='restore lights individually when reset, rather than restoring only all lights as a group when they all are in initial power-up state')

    args = parser.parse_args()
    bridge = get_bridge(args)
    lights = get_lights(bridge, args)
    if not lights:
        print("Error: No lights available", file=sys.stderr)
        sys.exit(3)
    try:
        do_monitor(bridge, args, lights)
    except KeyboardInterrupt:
        sys.exit(signal.SIGINT + 128)    # Terminate quietly on ^C
