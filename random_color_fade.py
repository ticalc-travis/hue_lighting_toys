#!/usr/bin/env python3

import argparse
import random
import sys
import time

import phue                     # https://github.com/studioimaginaire/phue

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

def run_show(bridge, args, lights):
    while True:
        h = random.randint(*args.hue_range)
        s = random.randint(*args.sat_range)
        b = random.randint(*args.bri_range)
        for L in lights:
            bridge.set_light(L.light_id, {'hue': h, 'sat': s, 'bri': b},
                             transitiontime=args.cycle_time)
            if not args.group_hue:
                h = random.randint(*args.hue_range)
            if not args.group_sat:
                s = random.randint(*args.sat_range)
            if not args.group_bri:
                b = random.randint(*args.bri_range)
        time.sleep(args.cycle_time / 10)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Produce a Philips Hue lighting random color fade effect.',
        epilog='If no lights are specified to be used, all lights found on the '
        'bridge will be used in the effect. '
        'The first time this script is run on a device, it may be necessary to '
        'press the button on the bridge before running the script so that it can '
        'be authenticated and be permitted to access the bridge and lighting '
        'system.')
    parser.add_argument(
        '-ln', '--light-number',
        dest='lights', action='append', type=int, metavar='LIGHT-NUM', nargs='+',
        help='include light number %(metavar)s in the effect')
    parser.add_argument(
        '-l', '--light-name',
        dest='lights', action='append', type=str, metavar='LIGHT-NAME', nargs='+',
        help='include light named %(metavar)s in the effect')
    parser.add_argument(
        '-b', '--bridge',
        dest='bridge_address',
        help='IP address or hostname of the Hue bridge to connect to')
    parser.add_argument(
        '-t', '--cycle-time',
        dest='cycle_time', type=int, metavar='DECISECONDS', default=100,
        help='use a speed of %(metavar)s tenths of a second per color cycle (default: %(default)s)')
    parser.add_argument(
        '-gh', '--group-hue',
        dest='group_hue', action='store_true',
        help='match the same hue among all lights')
    parser.add_argument(
        '-gs', '--group-saturation',
        dest='group_sat', action='store_true',
        help='match the same saturation among all lights')
    parser.add_argument(
        '-gb', '--group-brightness',
        dest='group_bri', action='store_true',
        help='match the same brightness among all lights')
    parser.add_argument(
        '-hr', '--hue-range',
        dest='hue_range', nargs=2, type=int, metavar=('L', 'H'),
        default=[0, 65535],
        help='restrict the generated hue range (0 to 65535) from L to H')
    parser.add_argument(
        '-sr', '--saturation-range',
        dest='sat_range', nargs=2, type=int, metavar=('L', 'H'),
        default=[0, 255],
        help='restrict the generated saturation range (0 to 255) from L to H')
    parser.add_argument(
        '-br', '--brightness-range',
        dest='bri_range', nargs=2, type=int, metavar=('L', 'H'),
        default=[1, 254],
        help='restrict the generated saturation range (1 to 254) from L to H')

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
