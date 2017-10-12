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

import time

from hue_toys.base import default_run
from hue_toys.coded_digits import CodedDigitsProgram


class CodedClockProgram(CodedDigitsProgram):
    """Blink out a series of color-coded digits representing the time of
    day.
    """

    def add_opts(self):
        self.add_main_opts()

    def main(self):
        while True:
            digits = time.strftime('%H%M')
            CodedDigitsProgram.flash_digits(self, digits)


def main():
    default_run(CodedClockProgram)
