#!/usr/bin/env python3

from time import time

from base import default_run
from coded_digits import CodedDigitsProgram


class CodedStopwatchProgram(CodedDigitsProgram):
    """Blink out a series of color-coded digits representing elapsed time.
    """

    def add_opts(self):
        self.add_main_opts()

    def main(self):
        start = time()
        while True:
            elapsed_secs = int(time() - start)
            hrs, mins = elapsed_secs // 3600, (elapsed_secs // 60) % 60
            if hrs:
                digits = '{}{:02}'.format(hrs, mins)
            else:
                digits = '{}'.format(mins)
            if self.opts.verbose:
                print('\r{}:{:02}    '.format(hrs, mins), end='',
                      flush=True)

            CodedDigitsProgram.flash_digits(self, digits)


if __name__ == '__main__':
    default_run(CodedStopwatchProgram)
