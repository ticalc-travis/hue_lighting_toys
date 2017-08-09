#!/usr/bin/env python3

import argparse
import math
import random
import sys
import time

import phue                     # https://github.com/studioimaginaire/phue

# The light parameters used to encode each character/digit
DIGITS_DEFAULT = 'bright'
DIGITS = {
    'dim': {
        '0': {'on': True, 'ct': 250, 'bri': 1},
        '1': {'on': True, 'hue': 46014, 'sat': 255, 'bri': 1},
        '2': {'on': True, 'hue': 7621, 'sat': 254, 'bri': 1},
        '3': {'on': True, 'hue': 24155, 'sat': 254, 'bri': 1},
        '4': {'on': True, 'hue': 10434, 'sat': 254, 'bri': 32},
        '5': {'on': True, 'hue': 0, 'sat': 255, 'bri': 1},
        '6': {'on': True, 'hue': 3901, 'sat': 255, 'bri': 32},
        '7': {'on': True, 'hue': 48913, 'sat': 218, 'bri': 1},
        '8': {'on': True, 'hue': 39280, 'sat': 236, 'bri': 32},
        '9': {'on': True, 'hue': 58368, 'sat': 254, 'bri': 1},
        # Default encoding for unrecognized characters; also used for
        # “strobe” transitions between characters
        None: {'on': False},
    },
    'bright': {
        '0': {'on': True, 'ct': 250, 'bri': 128},
        '1': {'on': True, 'hue': 46014, 'sat': 255, 'bri': 64},
        '2': {'on': True, 'hue': 7621, 'sat': 200, 'bri': 64},
        '3': {'on': True, 'hue': 24155, 'sat': 254, 'bri': 128},
        '4': {'on': True, 'hue': 10434, 'sat': 254, 'bri': 254},
        '5': {'on': True, 'hue': 0, 'sat': 255, 'bri': 128},
        '6': {'on': True, 'hue': 3901, 'sat': 255, 'bri': 254},
        '7': {'on': True, 'hue': 48913, 'sat': 218, 'bri': 128},
        '8': {'on': True, 'hue': 39280, 'sat': 236, 'bri': 254},
        '9': {'on': True, 'hue': 58368, 'sat': 254, 'bri': 128},
        # Default encoding for unrecognized characters; also used for
        # “strobe” transitions between characters
        None: {'on': False},
    },
}


def get_bridge(args):
    return phue.Bridge(args.bridge_address)

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

def group_digits(digits, num_lights):
    size_with_pad = math.ceil(len(digits) / num_lights) * num_lights
    padded_digits = '{:>{}}'.format(digits, size_with_pad)
    digit_groups = [padded_digits[i:i+num_lights]
                    for i in range(0, size_with_pad, num_lights)]
    return digit_groups

def run_show(bridge, args, lights):
    digit_groups = group_digits(args.digits, len(lights))
    digit_cmds = DIGITS[args.scheme]
    for digit_group in digit_groups:
        if args.switch_time > 0:
            bridge.set_light([L.light_id for L in lights],
                             digit_cmds[None], transitiontime=0)
            time.sleep(args.switch_time / 10)
        for digit, light in zip(digit_group, lights):
            cmd = digit_cmds.get(digit, digit_cmds[None])
            bridge.set_light(light.light_id, cmd, transitiontime=0)
        time.sleep(args.cycle_time / 10)
    if args.padded:
        bridge.set_light([L.light_id for L in lights],
                         digit_cmds[None], transitiontime=0)
        time.sleep(args.cycle_time / 10)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Blink out a series of digits encoded using colors.',
        epilog='Lights will be sequenced in the order specified. '
        'If no lights are specified to be used, all lights found on the '
        'bridge will be used in the effect. '
        'The first time this script is run on a device, it may be necessary to '
        'press the button on the bridge before running the script so that it can '
        'be authenticated and be permitted to access the bridge and lighting '
        'system.')
    parser.add_argument(
        '-ln', '--light-number',
        dest='lights', action='append', type=int, metavar='LIGHT-NUM', nargs='+',
        help='include light number %(metavar)s in the sequence')
    parser.add_argument(
        '-l', '--light-name',
        dest='lights', action='append', type=str, metavar='LIGHT-NAME', nargs='+',
        help='include light named %(metavar)s in the sequence')
    parser.add_argument(
        '-b', '--bridge',
        dest='bridge_address',
        help='IP address or hostname of the Hue bridge to connect to')
    parser.add_argument(
        '-t', '--cycle-time',
        dest='cycle_time', type=int, metavar='DECISECONDS', default=10,
        help='display each set of digits for %(metavar)s tenths of a second (default: %(default)s)')
    parser.add_argument(
        '-s', '--switch-time',
        dest='switch_time', type=int, metavar='DECISECONDS', default=2,
        help='display the "blank" color on all lights for %(metavar)s tenths of a second between digits (default: %(default)s. 0 makes it as short as possible; -1 disables it entirely.')
    parser.add_argument(
        '-p', '--pad',
        dest='padded', action='store_true',
        help='reset all lights to the "blank" color when the sequence finishes')
    parser.add_argument(
        '-c', '--scheme',
        dest='scheme', type=str, choices=DIGITS.keys(),
        default=DIGITS_DEFAULT,
        help='use the chosen color scheme')
    parser.add_argument(
        'digits', type=str,
        help='the sequence of digits to flash')

    args = parser.parse_args()
    bridge = get_bridge(args)
    lights = get_lights(bridge, args)
    if not lights:
        print("Error: No lights available", file=sys.stderr)
        sys.exit(3)
    try:
        run_show(bridge, args, lights)
    except KeyboardInterrupt:
        print()                 # Terminate quietly on ^C
