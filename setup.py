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

from setuptools import setup
from codecs import open
from os import path

with open(
        path.join(path.abspath(path.dirname(__file__)), 'README.adoc'),
        encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='hue_toys',
    version='0.0.0',
    description="Travis's assorted Philips Hue toys",
    long_description=long_description,
    url='https://github.com/ticalc-travis/hue_lighting_toys',
    author='Travis Evans',
    author_email='travisgevans@gmail.com',
    license='GPL',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: Home Automation',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='philips hue smart lighting',
    python_requires='>=3.5',
    packages=['hue_toys'],
    install_requires=['phue'],
    entry_points={
        'console_scripts': [
            'alt_lamp_simulation=hue_toys.alt_lamp_simulation:main',
            'chasing_colors=hue_toys.chasing_colors:main',
            'coded_clock=hue_toys.coded_clock:main',
            'coded_digits=hue_toys.coded_digits:main',
            'coded_stopwatch=hue_toys.coded_stopwatch:main',
            'fading_colors=hue_toys.fading_colors:main',
            'incandescent_fade=hue_toys.incandescent_fade:main',
            'lightctl=hue_toys.lightctl:main',
            'lightctl_curses=hue_toys.lightctl_curses:main',
            'power_fail_restore=hue_toys.power_fail_restore:main',
        ],
    },
)
