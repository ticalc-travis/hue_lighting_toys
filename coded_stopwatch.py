#!/usr/bin/env python3

import time

from base import default_run
from coded_digits import CodedDigitsProgram


class CodedStopwatchProgram(CodedDigitsProgram):

    def get_description(self):
        return 'Blink out a series of color-coded digits representing elapsed time.'

    def add_opts(self, parser):
        self.add_main_opts(parser)

    def run(self):
        start = time.time()
        while True:
            et = int(time.time() - start)
            hr, min = et // 3600, (et // 60) % 60
            if hr:
                digits = '{}{:02}'.format(hr, min)
            else:
                digits = '{}'.format(min)
            print('\r{}:{:02}    '.format(hr, min), end='', flush=True)

            CodedDigitsProgram.flash_digits(self, digits)


if __name__ == '__main__':
    default_run(CodedStopwatchProgram)
