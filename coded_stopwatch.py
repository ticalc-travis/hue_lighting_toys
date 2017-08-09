#!/usr/bin/env python3

import os
import sys
import time

def go():
    start = time.time()
    while True:
        et = int(time.time() - start)
        hr, min = et // 3600, (et // 60) % 60
        if hr:
            digits = '{}{:02}'.format(hr, min)
        else:
            digits = '{}'.format(min)
        opts = []
        if len(digits) == 1:
            opts += ['-s', '-1']
        else:
            opts += ['-p']
        print('\r{}:{:02}    '.format(hr, min), end='', flush=True)
        os.spawnv(os.P_WAIT, './coded_digits.py',
                  ['./coded_digits.py', digits] + opts + sys.argv[1:])

if __name__ == '__main__':
    try:
        go()
    except KeyboardInterrupt:
        print()

