#!/usr/bin/env python3

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

from collections import defaultdict
import curses
import logging
import threading
from time import sleep, time
import queue

from hue_toys.base import BaseProgram, default_run
from hue_toys.phue_helper import MIN, MAX, WIDTH, tungsten_cct, iconv_ct


MIN_BRIDGE_CMD_INTERVAL = .4
"""Minimum allowed time in seconds between light commands sent to Hue bridge"""


# Display layout:
#  0         1         2         3         4         5        6
#  012345678901234567890123456789012345678901234567890123456790
# 0
# 1 ID ##           Light name
# 2                 === Unreachable ===
# 3
# 4                 Power       [On ]      Brightness:   ###
# 5
# 6 > H/S           Hue:        #####      Saturation:   ###
# 7   XY            X:         #.####      Y:         #.####
# 8   CT            Mired:        ###      Kelvin:      ####
# 9
#10   Ext. CT       Mired:    #######      Kelvin: #########
#11   Ext. inc.     Incandescent: ###
#12
#13
#14 Next light    Previous light        Quit
#15 Refresh now   Auto-refresh [Off]
#16
#17 Left, Right, Tab, Backtab:  Move cursor
#18 Up, Down, 0-9:  Change value
#  012345678901234567890123456789012345678901234567890123456790
#  0         1         2         3         4         5        6


LABELS = [
    # role, row, col
    ('light_id', 1, 1),
    ('light_name', 1, 17),
    ('unreachable', 2, 17),
    ('power', 4, 29),
    ('hs_mode', 6, 1),
    ('xy_mode', 7, 1),
    ('ct_mode', 8, 1),
    ('ext_ct_mode', 10, 1),
    ('ext_inc_mode', 11, 1),
    ('auto-refresh', 15, 29),
    ('key_help_1', 17, 1),
    ('key_help_2', 18, 1),
]

HOTKEYS = [
    # group, action, label, row, col
    ('main', 'power', 'P&ower', 4, 17),
    ('main', 'bri', '&Brightness', 4, 40),
    ('hs', 'hue', '&Hue:', 6, 17),
    ('hs', 'sat', '&Saturation:', 6, 40),
    ('xy', 'x', '&X:', 7, 17),
    ('xy', 'y', '&Y:', 7, 40),
    ('ct', 'ct', '&Mired:', 8, 17),
    ('ct', 'ctk', '&Kelvin:', 8, 40),
    ('ext_ct', 'xct', 'Mir&ed:', 10, 17),
    ('ext_ct', 'xctk', 'Kel&vin', 10, 40),
    ('ext_inc', 'inc', '&Incandescent:', 11, 17),
    ('main', 'next', '&Next light', 14, 1),
    ('main', 'prev', '&Previous light', 14, 15),
    ('main', 'quit', '&Quit', 14, 37),
    ('main', 'refresh', '&Refresh now', 15, 1),
    ('main', 'toggle-auto-refresh', '&Auto-refresh', 15, 15),
]

KEY_HELP_1 = 'Left, Right, Tab, Backtab:  Move cursor'
KEY_HELP_2 = 'Up, Down, 0-9:  Change value'

OTHER_KEYS = [
    # key, action
    ('\t', 'next_field'),
    ('KEY_BTAB', 'prev_field'),

    ('KEY_RIGHT', 'next_char'),
    (' ', 'next_char'),
    ('KEY_LEFT', 'prev_char'),
    ('\x7f', 'prev_char'),
    ('KEY_BACKSPACE', 'prev_char'),
    ('\x08', 'prev_char'),

    ('KEY_UP', 'incr_digit'),
    ('KEY_DOWN', 'decr_digit'),
    ('0', 'enter_0'),
    ('1', 'enter_1'),
    ('2', 'enter_2'),
    ('3', 'enter_3'),
    ('4', 'enter_4'),
    ('5', 'enter_5'),
    ('6', 'enter_6'),
    ('7', 'enter_7'),
    ('8', 'enter_8'),
    ('9', 'enter_9'),
]

INPUT_FIELDS = {
    'main': [
        # name, width, min value, max value, row, col
        ('bri', WIDTH['bri'], MIN['bri'], MAX['bri'], 4, 54),
    ],
    'hs': [
        ('hue', WIDTH['hue'], MIN['hue'], MAX['hue'], 6, 29),
        ('sat', WIDTH['sat'], MIN['sat'], MAX['sat'], 6, 54),
    ],
    'xy': [
        ('x', WIDTH['xy'], MIN['xy'], MAX['xy'], 7, 28),
        ('y', WIDTH['xy'], MIN['xy'], MAX['xy'], 7, 51),
    ],
    'ct': [
        ('ct', WIDTH['ct'], MIN['ct'], MAX['ct'], 8, 31),
        ('ctk', WIDTH['ctk'], MIN['ctk'], MAX['ctk'], 8, 53),
    ],
    'ext_ct': [
        ('xct', WIDTH['xct'], MIN['xct'], MAX['xct'], 10, 27),
        ('xctk', WIDTH['xctk'], MIN['xctk'], MAX['xctk'], 10, 48),
    ],
    'ext_inc': [
        ('inc', WIDTH['inc'], MIN['inc'], MAX['inc'], 11, 31),
    ],
}



class CursorOutOfRangeError(ValueError):
    """Exception rasied when an attempt is made to place a field cursor past
    the beginning or end of its field
    """
    pass

class CursorBadPositionError(ValueError):
    """Exception raised when an attempt is made to place a field cursor on
    an illegal character within a field
    """
    pass


class UnsignedIntField():
    """Positive integer input field class

    Attributes:

    fmt_width, min_val, max_val:  Args passed to __init__

    cursor:  Current cursor position within field; 0 is leftmost
        position (most-significant digit)

    value:  Current numeric value held in field

    str_width (read-only):  Maximum display width of value in characters

    max_cursor (read-only):  Maximum valid cursor position
    """

    def __init__(self, fmt_width, min_val, max_val, value=None):
        """Args:  max width of int for display purposes, minimum allowable
        value, maximum allowable value
        """
        self.fmt_width = fmt_width
        self.min_val = min_val
        self.max_val = max_val

        self.value = value
        self._cursor = 0

    def __str__(self):
        """Return string representation of field's value"""
        if self.value is None:
            return '-' * self.fmt_width
        return self._format.format(self.value)

    @property
    def value(self):
        """Value getter"""
        return self._value

    @value.setter
    def value(self, new_value):
        """Set value, clipping it within self.min_val and self.max_val"""
        if new_value is None:
            self._value = new_value
        else:
            self._value = min(max(new_value, self.min_val), self.max_val)

    @property
    def _format(self):
        """Get the formatting string to be used for string conversion"""
        return '{{:>{}}}'.format(self.fmt_width)

    @property
    def str_width(self):
        """Getter for read-only attribute str_width, which is the expected
        on-screen width of the field in characters
        """
        return self.fmt_width      # Same as fmt_width for IntField

    @property
    def max_cursor(self):
        """Getter for read-only attribute max_cursor, which is the maximum valid
        cursor position
        """
        return self.str_width - 1

    @property
    def cursor(self):
        """Get cursor position in field"""
        return self._cursor

    @cursor.setter
    def cursor(self, pos):
        """Move cursor to given position (0: most-significant digit), or throw
        an exception if out of range
        """
        if not 0 <= pos <= self.max_cursor:
            raise CursorOutOfRangeError(
                'cursor must be in range 0 to %d' % self.max_cursor)
        self._cursor = pos

    def move_cursor(self, places):
        """Move the cursor position the given number of places to the right (if
        positive) or left (if negative). Raise an exception if cursor
        goes out of range.
        """
        self.cursor += places

    def adjust_digit(self, increment):
        """Change the digit at the cursor position by increment, applying
        carries/borrows
        """
        incr_value = 10**(self.fmt_width - self.cursor - 1) * increment
        self.value += incr_value

    def put_digit(self, digit_val):
        """Replace the digit at the cursor position with digit_val"""
        if not 0 <= digit_val <= 9 and isinstance(digit_val, int):
            raise ValueError('argument to put_digit must be an int from 0 to 9')
        str_ = str(self).replace(' ', '0')
        str_ = str_[0:self.cursor] + str(digit_val) + str_[self.cursor+1:]
        self.value = type(self.value)(str_)


class UnsignedDecimalField(UnsignedIntField):
    """A positive fixed-place decimal input field class

    Attributes:

    fmt_width, min_val, max_val:  Args passed to __init__

    cursor:  Current cursor position within field; 0 is leftmost
        position (most-significant digit). The decimal point is included
        in the numbering, but the cursor is not allowed on rest on the
        decimal point position.

    value:  Current numeric value held in field

    str_width (read-only):  Maximum display width of value in characters

    max_cursor (read-only):  Maximum valid cursor position
    """

    def __init__(self, fmt_width, min_val, max_val, value=None):
        """Args:

        fmt_width:  display format width in format (number of integer
        part digits, number of fractional part digits)

        min_val, max_val:  minimum and maximum allowable values
        """
        UnsignedIntField.__init__(self, fmt_width, min_val, max_val, value)

    def __str__(self):
        if self.value is None:
            return self._format.format(0).replace('0', '-')
        return self._format.format(self.value)

    @property
    def _format(self):
        return '{{:>{}.{}f}}'.format(*self.fmt_width)

    @property
    def str_width(self):
        # Number of all digits plus decimal point char
        return self.fmt_width[0] + self.fmt_width[1] + 1

    @property
    def cursor(self):
        """Get cursor position in field"""
        return self._cursor

    @cursor.setter
    def cursor(self, pos):
        """Move cursor to given position (0: most-significant digit), or throw
        an exception if out of range or on decimal point
        """
        if not 0 <= pos <= self.max_cursor:
            raise CursorOutOfRangeError(
                'cursor must be in range 0 to %d' % self.max_cursor)
        elif pos == self.fmt_width[0]:
            raise CursorBadPositionError(
                'cursor cannot be at decimal point position')
        self._cursor = pos

    def move_cursor(self, places):
        """Move the cursor position the given number of places to the right (if
        positive) or left (if negative). Raise an exception if cursor
        goes out of range.
        """
        if not places:
            return
        try:
            self.cursor += places
        except CursorBadPositionError:
            # Move cursor over past decimal point in the correct direction
            self.cursor += places + (1 if places > 0 else -1)

    def adjust_digit(self, increment):
        """Change the digit at the cursor position by increment, applying
        carries/borrows
        """
        if self.cursor < self.fmt_width[0]:
            incr_value = 10**(self.fmt_width[0] - self.cursor - 1) * increment
            self.value += incr_value
        else:
            incr_value = 10**-(self.cursor - self.fmt_width[0]) * increment
            self.value += incr_value


class BridgeUpdateQueue(queue.Queue):
    """A Queue object for transmitting update events from the UI thread to
    the bridge update thread
    """


class BridgeUpdateThread(threading.Thread):
    """A thread that accumulates light parameter changes and sends
    appropriate update commands to the Hue bridge, throttled at an
    appropriate rate
    """
    def __init__(self, bridge, bridge_lock, light_update_queue):
        """Args: Hue bridge object, bridge access lock, event queue for light
        changes made in UI
        """
        threading.Thread.__init__(self)
        self.bridge = bridge
        self.bridge_lock = bridge_lock
        self.queue = light_update_queue

        self.__pending_cmds = defaultdict(dict)

    def __update_bridge(self):
        """Send a pending command to the bridge, if one is available. Return
        True if there was a command to process, False otherwise.
        """
        try:
            light_id, cmd = self.__pending_cmds.popitem()
        except KeyError:
            return False
        else:
            with self.bridge_lock:
                self.bridge.set_light(light_id, cmd)
            return True

    def run(self):
        """Start processing. Collect commands from event queue in the form
        (light_id, parameter, value) as they come in, rolling the
        updates into bridge update commands at the proper interval. A
        queue item of None signals the thread to shut down once all
        pending items sent before None have been processed.
        """
        cmd_interval = MIN_BRIDGE_CMD_INTERVAL
        last_update_time = 0
        while True:
            if time() - last_update_time >= cmd_interval:
                if self.__update_bridge():
                    last_update_time = time()

            # Wait for event until next bridge update is due
            wait_time = cmd_interval - ((time() - last_update_time) % cmd_interval)
            try:
                event = self.queue.get(timeout=wait_time)
            except queue.Empty:
                pass
            else:
                if event is None:
                    break
                light_id, param, value = event
                self.__pending_cmds[light_id][param] = value
                self.queue.task_done()

        # Shutdown time, flush remaining bridge updates and quit
        while self.__update_bridge():
            sleep(cmd_interval)



class LightControlProgram(BaseProgram):
    """A simple curses utility to control Hue lights"""

    def __init__(self, *args, **kwargs):
        logging.basicConfig(level=logging.CRITICAL)
        BaseProgram.__init__(self, *args, **kwargs)

        self.bridge_lock = threading.Lock()
        self.light_update_queue = queue.Queue()
        self.light_update_thread = BridgeUpdateThread(
            self.bridge, self.bridge_lock, self.light_update_queue)
        self.screen = None

        self.keys = {}
        self.fields = {}
        self.need_repaint = True
        self._auto_refresh_mode = False
        self._curr_light_idx = None
        self._curr_light = {}
        self._curr_group = None
        self._curr_field = {}

    def add_light_state_opt(self):
        pass

    def add_verbose_opt(self):
        pass

    def add_opts(self):
        BaseProgram.add_opts(self)

        self.opt_parser.add_argument(
            '-a', '--auto-refresh-mode',
            dest='auto_refresh_mode', action='store_true',
            help='start in auto-refresh mode')
        self.opt_parser.add_argument(
            '-t', '--auto-refresh-interval',
            dest='auto_refresh_interval', type=self.int_within_range(1, None),
            metavar='DECISECONDS', default=10,
            help='time in tenths of a second between auto-refresh updates (default: 10)')

    def is_group_active(self, group):
        """Is a widget of group active at the moment?"""
        return group == 'main' or group == self.curr_group

    def refresh_light(self, soft=False):
        """Refetch current light's data, update all fields, and repaint the
        UI. If not soft, also check the colormode and change the active
        field group (which may move the cursor) as well as repopulate
        the extended parameters that aren't tracked by the bridge
        """
        # Retrieve light info
        light_id = self.lights[self.curr_light_idx]
        with self.bridge_lock:
            light_info = self.bridge.get_light(light_id)
        # Workaround for soft refresh: if light is currently off, don't
        # update anything besides on/off state and reachable status, so
        # that user-entered fields don't vanish unless something else
        # turns on the light and starts manipulating it
        update_fields_ok = True
        if light_info['state']['on'] or not soft or not self._curr_light:
            self._curr_light = light_info
        else:
            self._curr_light['state']['on'] = light_info['state']['on']
            self._curr_light['state']['reachable'] = light_info['state']['reachable']
            update_fields_ok = False
        self._curr_light['id'] = light_id

        # Update input fields
        if update_fields_ok:
            # Sanitize input from bridge in case it happens to be insane
            # (it happened to me once!)
            light_state = self.bridge.sanitized_light_state(self.curr_light['state'])

            for field_name in ('bri', 'hue', 'sat', 'ct'):
                self.fields[field_name].value = light_state[field_name]
            self.fields['x'].value, self.fields['y'].value = light_state['xy']
            self.fields['ctk'].value = iconv_ct(light_state['ct'])
            if not soft:
                self.fields['xctk'].value = self.fields['ctk'].value
                self.fields['xct'].value = self.fields['ct'].value
                self.fields['inc'].value = light_state['bri']

        if not soft:
            # Change current group if new light's colormode is different
            # from the last one
            if not self.is_group_active(self._curr_light['state']['colormode']):
                self.curr_group = self._curr_light['state']['colormode']

        self.need_repaint = True

    @property
    def curr_light_idx(self):
        """Getter for self.ui_curr_light, which tracks the light currently being
        manipulated in the UI as an index into self.lights
        """
        return self._curr_light_idx

    @curr_light_idx.setter
    def curr_light_idx(self, light_idx):
        """Change the active light in the UI; retrieve that light's state and
        update the UI and its widgets
        """
        # Wrap light_index within range of self.lights and set it
        light_idx %= len(self.lights)
        self._curr_light_idx = light_idx

        # Update UI
        self.refresh_light()

    @property
    def curr_light(self):
        """Getter for active light's information. This attribute should not be
        directly written to.
        """
        return self._curr_light

    @property
    def curr_group(self):
        """Getter for self.ui_curr_group, which track the current light
        colormode and active UI fields for that colormode
        """
        return self._curr_group

    @curr_group.setter
    def curr_group(self, new_group):
        """Activate colormode group of input fields, moving cursor focus to
        first field of the new group if it was on a field not part of
        the new group
        """
        self._curr_group = new_group

        # Link together active fields in a chain representing navigation
        # order, wrapping around from the first field to the last field
        # and vice-versa
        field_names = [t[0] for t in
                       INPUT_FIELDS['main'] + INPUT_FIELDS[new_group]]
        for i, name in enumerate(field_names):
            try:
                self.fields[name].prv = self.fields[field_names[i-1]]
            except IndexError:
                self.fields[name].prv = self.fields[field_names[-1]]
            try:
                self.fields[name].nxt = self.fields[field_names[i+1]]
            except IndexError:
                self.fields[name].nxt = self.fields[field_names[0]]

        # Check field focus and change if it's on an inactive field
        if self.curr_field.group != new_group:
            self.curr_field = self.fields[field_names[0]]

        self.need_repaint = True

    @property
    def curr_field(self):
        """Getter for self.curr_field, which stores a dict entry from
        self.fields that the cursor is currently on
        """
        return self._curr_field

    @curr_field.setter
    def curr_field(self, field):
        """Set the current UI field to self.fields dict value 'field' and change
        the current group to the field's group if it isn't already
        """
        self._curr_field = field
        if not self.is_group_active(field.group):
            self.curr_group = field.group

    @property
    def auto_refresh_mode(self):
        return self._auto_refresh_mode

    @auto_refresh_mode.setter
    def auto_refresh_mode(self, value):
        if value:
            curses.halfdelay(self.opts.auto_refresh_interval)
        else:
            curses.cbreak()
        self.need_repaint = True
        self._auto_refresh_mode = value

    def init_ui(self):
        """Initialize UI and set up widget data structures"""

        self.auto_refresh_mode = self.opts.auto_refresh_mode

        # Key bindings
        for group, action, label, row, col in HOTKEYS:
            key = label[label.index('&') + 1].lower()
            self.keys[key] = action
        for key, action in OTHER_KEYS:
            self.keys[key] = action

        # Set up input field dictionary
        for group_name, group_list in INPUT_FIELDS.items():
            for name, width, min_val, max_val, row, col in group_list:
                if width[1]:
                    field = UnsignedDecimalField(width, min_val, max_val)
                else:
                    field = UnsignedIntField(width[0], min_val, max_val)
                self.fields[name] = field
                field.group = group_name
                field.name = name
                field.width = width
                field.row = row
                field.col = col
                field.nxt = field.prv = None
                # Define some more appropriate initial cursor locations
                # for certain “special” fields
                if name == 'xct':
                    field.default_cursor = field.max_cursor - 2
                elif name == 'xctk':
                    field.default_cursor = field.max_cursor - 3
                elif name == 'x' or name == 'y':
                    field.default_cursor = 2
                else:
                    field.default_cursor = 0
                field.cursor = field.default_cursor

        # Set initially focused field
        self.curr_field = self.fields['bri']

        # Set current light to first one listed on command line
        self.curr_light_idx = 0


    def _paint_on_indicator(self, row, col, is_on):
        """Draw an on/off indicator at row, col for status is_on (True if on,
        False if off
        """
        if is_on:
            attr, msg = curses.A_REVERSE, '[On ]'
        else:
            attr, msg = curses.A_NORMAL, '[Off]'
        self.screen.addstr(row, col, msg, attr)

    def _paint_mode_indicator(self, row, col, mode, label):
        """Paint mode's colormode indicator on the screen at row, col with label
        'label', according to the current field group
        """
        if self.is_group_active(mode):
            label = '> ' + label
            attr = curses.A_BOLD
        else:
            label = '  ' + label
            attr = curses.A_DIM
        self.screen.addstr(row, col, label, attr)

    def _paint_labels(self):
        """Draw informational text and values on the screen. Assumes screen has
        been cleared first.
        """
        for role, row, col in LABELS:
            if role == 'light_id':
                self.screen.addstr(row, col, 'ID #%d' % self.curr_light['id'])
            elif role == 'light_name':
                self.screen.addstr(row, col, self.curr_light['name'])
            elif role == 'unreachable':
                if not self.curr_light['state']['reachable']:
                    self.screen.addstr(row, col, '--- Unreachable ---',
                                       curses.A_BOLD)
            elif role == 'power':
                self._paint_on_indicator(row, col, self.curr_light['state']['on'])
            elif role == 'hs_mode':
                self._paint_mode_indicator(row, col, 'hs', 'H/S')
            elif role == 'xy_mode':
                self._paint_mode_indicator(row, col, 'xy', 'X,Y')
            elif role == 'ct_mode':
                self._paint_mode_indicator(row, col, 'ct', 'CT')
            elif role == 'ext_ct_mode':
                self._paint_mode_indicator(row, col, 'ext_ct', 'Ext. CT')
            elif role == 'ext_inc_mode':
                self._paint_mode_indicator(row, col, 'ext_inc', 'Ext. Inc.')
            elif role == 'auto-refresh':
                self._paint_on_indicator(row, col, self.auto_refresh_mode)
            elif role == 'key_help_1':
                self.screen.addstr(row, col, KEY_HELP_1)
            elif role == 'key_help_2':
                self.screen.addstr(row, col, KEY_HELP_2)
            else:
                assert False, 'Undefined window label role'

    def _paint_hotkeys(self):
        """Draw the hotkey “buttons” on the screen."""
        for group, _, label, row, col in HOTKEYS:
            highlight_pos = label.index('&')
            highlight_char = label[highlight_pos + 1]
            text_out = label.replace('&', '', 1)
            if self.is_group_active(group):
                attr = curses.A_NORMAL
                highlight_attr = curses.A_UNDERLINE | curses.A_BOLD
            else:
                attr = curses.A_DIM
                highlight_attr = curses.A_UNDERLINE | curses.A_NORMAL
            self.screen.addstr(row, col, text_out, attr)
            self.screen.addstr(row, col + highlight_pos, highlight_char,
                               highlight_attr)

    def paint_field(self, field):
        """Redraw the contents of the screen field given field dict from
        self.fields
        """
        if self.is_group_active(field.group):
            attr = curses.A_NORMAL
        else:
            attr = curses.A_DIM
        self.screen.addstr(field.row, field.col, str(field), attr)

    def put_cursor(self):
        """Move the terminal cursor to the position in the focused field where
        user input will next take place
        """
        self.screen.move(
            self.curr_field.row, self.curr_field.col + self.curr_field.cursor)

    def repaint_screen(self):
        """Clear the screen and fully redraw the UI with all fields and widgets"""
        self.screen.clear()
        self._paint_labels()
        self._paint_hotkeys()
        for field in self.fields.values():
            self.paint_field(field)

    def next_char(self, cursor_out_reset=False):
        """Move the cursor forward on the current field, or move focus to the
        beginning of the next field if it would move past the end. If
        the latter happens and cursor_out_reset, move the cursor on the
        previously-focused field back to its default position.
        """
        try:
            self.curr_field.move_cursor(1)
        except CursorOutOfRangeError:
            if cursor_out_reset:
                self.curr_field.cursor = self.curr_field.default_cursor
            self.curr_field = self.curr_field.nxt
            self.curr_field.cursor = 0

    def prev_char(self):
        """Move the cursor backward on the current field, or move it to the end
        of the previous field if it moves past the beginning
        """
        try:
            self.curr_field.move_cursor(-1)
        except CursorOutOfRangeError:
            self.curr_field = self.curr_field.prv
            self.curr_field.cursor = self.curr_field.max_cursor

    def send_light_update(self, field):
        """Translate the given field's value into a Hue bridge command and
        signal the update thread to send it
        """
        light_id = self.curr_light['id']

        if field.name in ('bri', 'hue', 'sat', 'inc', 'ct'):
            self.light_update_queue.put((light_id, field.name, field.value))
        elif field.name in ('x', 'y'):
            x, y = self.fields['x'].value, self.fields['y'].value
            self.light_update_queue.put((light_id, 'xy', [x, y]))
        elif field.name == 'ctk':
            # Translate to mired in order to use the normal API parameter
            ct = iconv_ct(field.value)
            self.light_update_queue.put((light_id, 'ct', ct))
        elif field.name == 'xct':
            # Translate to Kelvin and use the extended 'ctk' parameter
            # in the phue_helper's Bridge.set_light method
            ctk = iconv_ct(field.value)
            self.light_update_queue.put((light_id, 'ctk', ctk))
        elif field.name == 'xctk':
            # Send directly to extended 'ctk' parameter
            self.light_update_queue.put((light_id, 'ctk', field.value))

    def update_field(self, field, send_light_update=True):
        """Repaint the display of the given field and recalculate and redisplay
        any other fields affected by it. If send_light_update, also call
        self.send_light_update(field).
        """
        self.paint_field(field)

        if field.name == 'inc':
            # The 'inc' parameter modifies 'bri' and extended
            # color temperature parameters to match, so update
            # them, too
            self.fields['bri'].value = field.value
            self.paint_field(self.fields['bri'])
            # This calculation is (should be) the same as what
            # phue_helper.py uses for converting 'inc' to color
            # temperature
            self.fields['xctk'].value = int(tungsten_cct(
                self.fields['bri'].value))
            self.update_field(self.fields['xctk'], send_light_update=False)
        elif field.name == 'ct':
            # Likewise for mired vs. Kelvin…
            self.fields['ctk'].value = iconv_ct(field.value)
            self.paint_field(self.fields['ctk'])
        elif field.name == 'ctk':
            self.fields['ct'].value = iconv_ct(field.value)
            self.paint_field(self.fields['ct'])
        elif field.name == 'xct':
            self.fields['xctk'].value = iconv_ct(field.value)
            self.paint_field(self.fields['xctk'])
        elif field.name == 'xctk':
            self.fields['xct'].value = iconv_ct(field.value)
            self.paint_field(self.fields['xct'])

        if send_light_update:
            self.send_light_update(field)

    def toggle_power(self):
        """Toggle the on/off state of the current light. If light is turned on,
        update it with all the field parameters that have changed in the
        meantime (which the bridge does not normally accept when the
        light is off).
        """
        light_id = self.curr_light['id']
        light_was_on = self.curr_light['state']['on']
        self.light_update_queue.put((light_id, 'on', not light_was_on))

        self.curr_light['state']['on'] = not self.curr_light['state']['on']
        if not light_was_on:
            for field in self.fields.values():
                if self.is_group_active(field.group):
                    self.send_light_update(field)
        self.need_repaint = True

    def get_key_event(self):
        """Wait for a key and return a string representing the action to perform
        for that key
        """
        self.put_cursor()
        try:
            key = self.screen.getkey()
        except curses.error:
            # Refresh light for auto-fresh mode, in which curses
            # halfdelay mode is set
            return 'auto-refresh'
        try:
            return self.keys[key]
        except KeyError:
            return 'bad_key'

    def handle_action(self, action):
        """Perform appropriate UI action according to action string:

        - If action is the name of a field, focus that field

        - If it's 'next' or 'prev', change to next/previous light

        - If 'next_field', 'prev_field', 'next_char', 'prev_char', move
          cursor to next/prev field or next/prev character in field

        - If 'incr_digit', 'decr_digit', increment/decrement digit on cursor

        - If '0' through '9', enter that digit into field at cursor
          position and advance cursor

        - If 'refresh' or 'auto-refresh', refetch light data and repaint
          screen (if 'auto-refresh', perform a “soft” refresh that tries
          to leave the cursor position alone)

        - If 'toggle-auto-refresh', toggle auto-refresh mode
        """
        if action in self.fields:
            self.curr_field = self.fields[action]
        elif action == 'next':
            self.curr_light_idx += 1
        elif action == 'prev':
            self.curr_light_idx -= 1
        elif action == 'next_field':
            self.curr_field = self.curr_field.nxt
        elif action == 'prev_field':
            self.curr_field = self.curr_field.prv
        elif action == 'next_char':
            self.next_char()
        elif action == 'prev_char':
            self.prev_char()

        elif action == 'power':
            self.toggle_power()

        elif action == 'incr_digit':
            self.curr_field.adjust_digit(1)
            self.update_field(self.curr_field)
        elif action == 'decr_digit':
            self.curr_field.adjust_digit(-1)
            self.update_field(self.curr_field)
        elif action.startswith('enter_'):
            self.curr_field.put_digit(int(action.split('_', 1)[1]))
            self.update_field(self.curr_field)
            self.next_char(cursor_out_reset=True)

        elif action == 'refresh':
            self.refresh_light()
        elif action == 'auto-refresh':
            self.refresh_light(soft=True)
        elif action == 'toggle-auto-refresh':
            self.auto_refresh_mode = not self.auto_refresh_mode

    def curses_main(self, screen):
        """The main application method to be called after the curses screen has
        been set up
        """
        self.screen = screen
        self.init_ui()
        self.light_update_thread.start()

        while True:
            if self.need_repaint:
                self.repaint_screen()
                self.need_repaint = False

            action = self.get_key_event()
            if action == 'quit':
                break
            self.handle_action(action)

    def main(self):
        try:
            curses.wrapper(self.curses_main)
        finally:
            # Signal bridge update thread to terminate
            self.light_update_queue.put(None)


def main():
    default_run(LightControlProgram)
