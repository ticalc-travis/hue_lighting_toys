#!/usr/bin/env python3

def kelvin_to_xy(k):
    if k < 4000:
        x = -.2661239*(10e8/k**3) - .2343580*(10e5/k**2) + .8776956*(10e2/k) + .179910
    else:
        x = -3.0258469*(10e8/k**3) + 2.1070379*(10e5/k**2) + .2226347*(10e2/k) + .240390
    if k < 2222:
        y = -1.1063814*x**3 - 1.34811020*x**2 + 2.18555832*x - .20219683
    elif k < 4000:
        y = -.9549476*x**3 - 1.37418593*x**2 + 2.09137015*x - .16748867
    else:
        y = 3.0817580*x**3 - 5.87338670*x**2 + 3.75112997*x - .37001483
    return [x, y]

def kelvin_to_xy_2(k):
    u = (.860117757 + 1.54118254*10**-4 * k + 1.28641212 * 10**-7 * k**2) / (1 + 8.42420235 * 10**-4 * k + 7.08145163 * 10**-7 * k**2)
    v = (.317398726 + 4.22806245 * 10**-5 * k + 4.20481691 * 10**- 8 * k**2) / (1 - 2.89741816 * 10**-5 * k + 1.61456053 * 10**-7 * k**2)
    x = (3*u) / (2*u - 8*v + 4)
    y = (2*v) / (2*u - 8*v + 4)
    return [x,y]

def tungsten_cct(brightness):
    """Return an approximate tungesten color tempearture in Kelvin for an
incandescent light dimmed to the given brightness level.
    """
    return 5.63925392181 * brightness + 1423.98106079
