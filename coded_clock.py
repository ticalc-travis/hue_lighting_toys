#!/usr/bin/env python3

import time

from base import default_run
from coded_digits import CodedDigitsProgram


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


if __name__ == '__main__':
    default_run(CodedClockProgram)
