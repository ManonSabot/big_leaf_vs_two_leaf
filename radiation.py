#!/usr/bin/env python
"""
Various radiation funcs needed for the two-leaf approximation
"""

import sys
import numpy as np
import math
import constants as c

__author__  = "Martin De Kauwe"
__version__ = "1.0 (09.11.2018)"
__email__   = "mdekauwe@gmail.com"


def spitters(doy, sw_rad, cos_zenith):

    """
    Spitters algorithm to estimate the diffuse component from the measured
    irradiance.

    Eqn 20a-d.

    Parameters:
    ----------
    doy : int
        day of year
    sw_rad : double
        total incident radiation [J m-2 s-1]

    Returns:
    -------
    diffuse : double
        diffuse component of incoming radiation (returned in cw structure)

    References:
    ----------
    * Spitters, C. J. T., Toussaint, H. A. J. M. and Goudriaan, J. (1986)
      Separating the diffuse and direct component of global radiation and
      its implications for modeling canopy photosynthesis. Part I.
      Components of incoming radiation. Agricultural Forest Meteorol.,
      38:217-229.
    """

    #sine of the elev of the sun above the horizon is the same as cos_zen
    So = calc_extra_terrestrial_rad(doy, cos_zenith)

    # atmospheric transmisivity
    tau = estimate_clearness(sw_rad, So)

    cos_zen_sq = cos_zenith * cos_zenith

    # For zenith angles > 80 degrees, diffuse_frac = 1.0
    if cos_zenith > 0.17:

        # Spitters formula
        R = 0.847 - 1.61 * cos_zenith + 1.04 * cos_zen_sq
        K = (1.47 - R) / 1.66
        if tau <= 0.22:
            diffuse_frac = 1.0
        elif tau > 0.22 and tau <= 0.35:
            diffuse_frac = 1.0 - 6.4 * (tau - 0.22) * (tau - 0.22)
        elif tau > 0.35 and tau <= K:
            diffuse_frac = 1.47 - 1.66 * tau
        else:
            diffuse_frac = R

    else:
        diffuse_frac = 1.0

    # doubt we need this, should check
    if diffuse_frac <= 0.0:
        diffuse_frac = 0.0
    elif diffuse_frac >= 1.0:
        diffuse_frac = 1.0

    direct_frac = 1.0 - diffuse_frac

    return (diffuse_frac, direct_frac)

def estimate_clearness(sw_rad, So):
    """
    Estimate atmospheric transmisivity - the amount of diffuse radiation
    is a function of the amount of haze and/or clouds in the sky. Estimate
    a proxy for this, i.e. the ratio between global solar radiation on a
    horizontal surface at the ground and the extraterrestrial solar
    radiation
    """

    # catch possible divide by zero when zenith = 90.
    if So <= 0.0:
        tau = 0.0;
    else:
        tau = sw_rad / So


    if tau > 1.0:
        tau = 1.0;
    elif tau < 0.0:
        tau = 0.0;


    return (tau)


def calculate_solar_geometry(doy, hod, latitude, longitude):
    """
    The solar zenith angle is the angle between the zenith and the centre
    of the sun's disc. The solar elevation angle is the altitude of the
    sun, the angle between the horizon and the centre of the sun's disc.
    Since these two angles are complementary, the cosine of either one of
    them equals the sine of the other, i.e. cos theta = sin beta. I will
    use cos_zen throughout code for simplicity.
    Arguments:
    ----------
    doy : double
        day of year
    hod : double:
        hour of the day [0.5 to 24]
    Returns:
    --------
    cos_zen : double
        cosine of the zenith angle of the sun in degrees (returned)
    elevation : double
        solar elevation (degrees) (returned)
    References:
    -----------
    * De Pury & Farquhar (1997) PCE, 20, 537-557.
    """

    # need to convert 30 min data, 0-47 to 0-23.5
    hod /= 2.0

    gamma = day_angle(doy)
    rdec = calculate_solar_declination(doy, gamma)
    et = calculate_eqn_of_time(gamma)
    t0 = calculate_solar_noon(et, longitude)
    h = calculate_hour_angle(hod, t0)
    rlat = latitude * np.pi / 180.0 # radians

    # A13 - De Pury & Farquhar
    sin_beta = np.sin(rlat) * np.sin(rdec) + np.cos(rlat) * \
                np.cos(rdec) * np.cos(h)
    cos_zenith = sin_beta # The same thing, going to use throughout
    if cos_zenith > 1.0:
        cos_zenith = 1.0
    elif cos_zenith < 0.0:
        cos_zenith = 0.0

    return cos_zenith

def day_angle(doy):
    """
    Calculation of day angle - De Pury & Farquhar, '97: eqn A18
    Reference:
    ----------
    * De Pury & Farquhar (1997) PCE, 20, 537-557.
    * J. W. Spencer (1971). Fourier series representation of the position of
      the sun.
    Returns:
    ---------
    gamma - day angle in radians.
    """
    return (2.0 * np.pi * (float(doy) - 1.0) / 365.0)

def calculate_solar_declination(doy, gamma):
    """
    Solar Declination Angle is a function of day of year and is indepenent
    of location, varying between 23deg45' to -23deg45'
    Arguments:
    ----------
    doy : int
        day of year, 1=jan 1
    gamma : double
        fractional year (radians)
    Returns:
    --------
    dec: float
        Solar Declination Angle [radians]
    Reference:
    ----------
    * De Pury & Farquhar (1997) PCE, 20, 537-557.
    * Leuning et al (1995) Plant, Cell and Environment, 18, 1183-1200.
    * J. W. Spencer (1971). Fourier series representation of the position of
      the sun.
    """

    # Solar Declination Angle (radians) A14 - De Pury & Farquhar
    decl = -23.4 * (np.pi / 180.) * np.cos(2.0 * np.pi *\
            (float(doy) + 10.) / 365.);

    return decl

def calculate_eqn_of_time(gamma):
    """
    Equation of time - correction for the difference btw solar time
    and the clock time.
    Arguments:
    ----------
    doy : int
        day of year
    gamma : double
        fractional year (radians)
    References:
    -----------
    * De Pury & Farquhar (1997) PCE, 20, 537-557.
    * Campbell, G. S. and Norman, J. M. (1998) Introduction to environmental
      biophysics. Pg 169.
    * J. W. Spencer (1971). Fourier series representation of the position of
      the sun.
    * Hughes, David W.; Yallop, B. D.; Hohenkerk, C. Y. (1989),
      "The Equation of Time", Monthly Notices of the Royal Astronomical
      Society 238: 1529–1535
    """


    #
    # from Spencer '71. This better matches the de Pury worked example (pg 554)
    # The de Pury version is this essentially with the 229.18 already applied
    # It probably doesn't matter which is used, but there is some rounding
    # error below (radians)
    #
    et = 0.000075 + 0.001868 * np.cos(gamma) - 0.032077 * np.sin(gamma) -\
         0.014615 * np.cos(2.0 * gamma) - 0.04089 * np.sin(2.0 * gamma)

    # radians to minutes
    et *= 229.18;

    return et

def calculate_solar_noon(et, longitude):
    """
    Calculation solar noon - De Pury & Farquhar, '97: eqn A16
    Reference:
    ----------
    * De Pury & Farquhar (1997) PCE, 20, 537-557.
    Returns:
    ---------
    t0 - solar noon (hours).
    """

    # all international standard meridians are multiples of 15deg east/west of
    # greenwich
    Ls = round_to_value(longitude, 15.)
    t0 = 12.0 + (4.0 * (Ls - longitude) - et) / 60.0

    return t0

def round_to_value(number, roundto):
    return (round(number / roundto) * roundto)

def calculate_hour_angle(t, t0):
    """
    Calculation solar noon - De Pury & Farquhar, '97: eqn A15
    Reference:
    ----------
    * De Pury & Farquhar (1997) PCE, 20, 537-557.
    Returns:
    ---------
    h - hour angle (radians).
    """
    return (np.pi * (t - t0) / 12.0)

def calc_extra_terrestrial_rad(doy, cos_zenith):
    """
    Solar radiation incident outside the earth's atmosphere, e.g.
    extra-terrestrial radiation. The value varies a little with the earths
    orbit.
    Using formula from Spitters not Leuning!
    Arguments:
    ----------
    doy : double
        day of year
    cos_zenith : double
        cosine of zenith angle (radians)
    Returns:
    --------
    So : float
        solar radiation normal to the sun's bean outside the Earth's atmosphere
        (J m-2 s-1)
    Reference:
    ----------
    * Spitters et al. (1986) AFM, 38, 217-229, equation 1.
    """

    # Solar constant (J m-2 s-1)
    Sc = 1370.0

    if cos_zenith > 0.0:
        #
        # remember sin_beta = cos_zenith; trig funcs are cofuncs of each other
        # sin(x) = cos(90-x) and cos(x) = sin(90-x).
        #
        So = Sc * (1.0 + 0.033 * np.cos(doy / 365.0 * 2.0 * np.pi)) * cos_zenith
    else:
        So = 0.0

    return So

def calculate_absorbed_radiation(par, cos_zenith, lai, direct_frac,
                                 diffuse_frac):
    """
    Calculate absorded irradiance of sunlit and shaded fractions of
    the canopy. The total irradiance absorbed by the canopy and the
    sunlit/shaded components are all expressed on a ground-area basis!
    NB:  sin_beta == cos_zenith

    References:
    -----------
    * De Pury & Farquhar (1997) PCE, 20, 537-557.
    but see also:
    * Wang and Leuning (1998) AFm, 91, 89-111.
    * Dai et al. (2004) Journal of Climate, 17, 2281-2299.
    """

    rho_cd = 0.036                    # canopy reflect coeff for diffuse PAR
    rho_cb = 0.029                    # canopy reflect coeff for direct PAR
    omega = 0.15                      # leaf scattering coefficient of PAR
    k_dash_b = 0.46 / cos_zenith      # beam & scat PAR ext coef
    k_dash_d = 0.719                  # diffuse & scattered PAR extinction coeff
    lad = 0                           # NB. default is to assume spherical LAD=0

    apar_leaf = np.zeros(2) # sunlit, shaded
    lai_leaf = np.zeros(2)  # sunlit, shaded
    #
    # Ross-Goudriaan function is the ratio of the projected area of leaves
    # in the direction perpendicular to the direction of incident solar
    # radiation and the actual leaf area. See Sellers (1985), eqn 13/
    # note this is taken from CABLE code (Kowalczyk '06, eqn 28/29)
    #
    psi1 = 0.5 - 0.633 * lad
    psi2 = 0.877 * (1.0 - 2.0 * psi1)
    Gross = psi1 + psi2 * cos_zenith

    # beam extinction coefficient for black leaves
    kb = Gross / cos_zenith

    # Direct-beam irradiance absorbed by sunlit leaves - de P & F, eqn 20b
    Ib = par * direct_frac
    beam = Ib * (1.0 - omega) * (1.0 - np.exp(-kb * lai))

    # Diffuse irradiance absorbed by sunlit leaves - de P & F, eqn 20c
    Id = par * diffuse_frac
    arg1 = Id * (1.0 - rho_cd)
    arg2 = 1.0 - np.exp(-(k_dash_d + kb) * lai)
    arg3 = k_dash_d / (k_dash_d + kb)
    shaded = arg1 * arg2 * arg3

    # Scattered-beam irradiance abs. by sunlit leaves - de P & F, eqn 20d
    arg1 = (1.0 - rho_cb) * (1.0 - np.exp(-(k_dash_b + kb) * lai))
    arg2 = k_dash_b / (k_dash_b + kb)
    arg3 = (1.0 - omega) * (1.0 - np.exp(-2.0 * kb * lai)) / 2.0
    scattered = Ib * (arg1 * arg2 - arg3)

    # Total irradiance absorbed by the canopy (Ic) - de P & F, eqn 13
    arg1 = (1.0 - rho_cb) * Ib * (1.0 - np.exp(-k_dash_b * lai))
    arg2 = (1.0 - rho_cd) * Id * (1.0 - np.exp(-k_dash_d * lai))
    total_canopy_irradiance = arg1 + arg2

    # Irradiance absorbed by the sunlit fraction of the canopy
    apar_leaf[c.SUNLIT] = beam + scattered + shaded

    # Irradiance absorbed by the shaded fraction of the canopy
    apar_leaf[c.SHADED] = total_canopy_irradiance - apar_leaf[c.SUNLIT]

    # Calculate sunlit &shdaded LAI of the canopy - de P * F eqn 18
    lai_leaf[c.SUNLIT] = (1.0 - np.exp(-kb * lai)) / kb
    lai_leaf[c.SHADED] = lai - lai_leaf[c.SUNLIT]

    return (apar_leaf, lai_leaf, kb)