#!/usr/bin/env python3

import curses

import phue
from hue_helper import kelvin_to_xy_2

def get_bridge():
    return phue.Bridge()

def my_incr_colortemp(light, incr):
    try:
        light.my_colortemp_k += incr
    except AttributeError:
        light.my_colortemp_k = light.colortemp_k + incr
    light.xy = kelvin_to_xy_2(light.my_colortemp_k)

def main(stdscr):
    bridge = get_bridge()
    lights = bridge.get_light_objects()
    curr_light_no = 0
    curr_incr_i = 2
    increments = [1, 5, 10, 50, 100, 500, 1000, 5000, 10000]

    while True:
        curr_light = lights[curr_light_no]
        curr_light.transitiontime = None
        incr = increments[curr_incr_i]

        stdscr.clear()
        stdscr.addstr('Light %d: %s\n' % (curr_light_no + 1, curr_light.name))
        stdscr.addstr('\n')
        stdscr.addstr('Incr: %5d\n' % increments[curr_incr_i])
        stdscr.addstr('\n')
        stdscr.addstr('%s  Bri:  %3d   Hue:   %5d   Sat: %3d\n' % (
            'On ' if curr_light.on else 'Off',
            curr_light.brightness, curr_light.hue, curr_light.saturation))
        try:
            ext_tempk_str = '   ExtTempK: %4d' % curr_light.my_colortemp_k
        except AttributeError:
            ext_tempk_str = ''
        stdscr.addstr('     Temp: %3d   TempK:  %4d%s\n' % (
            curr_light.colortemp, curr_light.colortemp_k, ext_tempk_str))
        stdscr.addstr('\n\n' if curr_light.reachable else
                      '\n --- Unreachable light ---\n')

        c = stdscr.getch()

        if c == curses.KEY_DOWN:
            curr_light_no -= 1
            if curr_light_no < 0:
                curr_light_no = len(lights) - 1
        elif c == curses.KEY_UP:
            curr_light_no += 1
            if curr_light_no >= len(lights):
                curr_light_no = 0

        elif c == curses.KEY_LEFT:
            curr_incr_i -= 1
            if curr_incr_i < 0:
                curr_incr_i = len(increments) - 1
        elif c == curses.KEY_RIGHT:
            curr_incr_i += 1
            if curr_incr_i >= len(increments):
                curr_incr_i = 0

        elif c == ord(' '):
            curr_light.on = not curr_light.on
        elif c == ord(',') or c == ord('B'):
            curr_light.brightness -= incr
        elif c == ord('.') or c == ord('b'):
            curr_light.brightness += incr

        elif c == ord('t'):
            curr_light.colortemp += incr
        elif c == ord('T'):
            curr_light.colortemp -= incr
        elif c == ord('k'):
            my_incr_colortemp(curr_light, incr)
        elif c == ord('K'):
            my_incr_colortemp(curr_light, -incr)

        elif c == ord('h'):
            curr_light.hue += incr
        elif c == ord('H'):
            curr_light.hue -= incr
        elif c == ord('s'):
            curr_light.saturation += incr
        elif c == ord('S'):
            curr_light.saturation -= incr

        elif c == ord('q'):
            break

if __name__ == '__main__':
    curses.wrapper(main)
