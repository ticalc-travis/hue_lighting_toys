#!/usr/bin/env python3

import argparse
import random
import signal
import sys
import threading
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

def turn_on_lights(bridge, lights):
    for L in lights:
        bridge.set_light(L.light_id, 'on', True)

def run_show(bridge, bridge_lock, args, light_id):
    randint = random.randint

    stages = []
    have_pink_stage = random.randint(0, 1)
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
                       'ct': 286,
                       'transitiontime': 0})
        stages.append({'bri': 254,
                       'transitiontime': randint(800, 1600)})

    for stage in stages:
        with bridge_lock:
            bridge.set_light(light_id, stage)
        time.sleep(stage.get('transitiontime', 40)/10 + .1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Produce a Philips Hue lighting simulation of certain CFLs.',
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

    args = parser.parse_args()
    bridge = get_bridge(args)
    bridge_lock = threading.Lock()
    lights = get_lights(bridge, args)
    if not lights:
        print("Error: No lights available", file=sys.stderr)
        sys.exit(3)
    turn_on_lights(bridge, lights)

    threads = []
    for L in lights:
        t = threading.Thread(
            target=run_show,
            args=(bridge, bridge_lock, args, L.light_id),
            daemon=True)
        threads.append(t)
        t.start()
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        sys.exit(signal.SIGINT + 128)    # Terminate quietly on ^C
