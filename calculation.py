import operator
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


from pyirf.cuts import evaluate_binned_cut

from astropy.time import Time
from astropy.coordinates import SkyCoord, SkyOffsetFrame, AltAz, EarthLocation
import astropy.units as u
from astropy import table

from astropy.coordinates.erfa_astrom import erfa_astrom, ErfaAstromInterpolator


erfa_astrom.set(ErfaAstromInterpolator(10 * u.min))


def calc_ontime(df):
    delta = np.diff(df.time.sort_values())
    delta = delta[np.abs(delta) < 10]
    return len(df) * delta.mean() * u.s


def calc_theta_off(source_coord: SkyCoord, reco_coord: SkyCoord, pointing_coord: SkyCoord, n_off=5):
    wobble_dist = source_coord.separation(pointing_coord)
    source_angle = pointing_coord.position_angle(source_coord)

    theta_offs = []
    for off in (np.arange(360 / (n_off + 1), 360, 360 / (n_off + 1)) * u.deg):
        off_position = pointing_coord.directional_offset_by(
            separation=wobble_dist,
            position_angle=source_angle + off
        )
        theta_offs.append(off_position.separation(reco_coord))

    return reco_coord.separation(source_coord), np.concatenate(theta_offs)


def read_run_calculate_thetas(run, threshold, source: SkyCoord, n_offs):

    df = pd.read_hdf(run, key = '/dl2/event/telescope/tel_001/table')

    ontime = calc_ontime(df).to(u.hour)

    if type(threshold) == float:
        df_selected = df.query(f'gamma_prediction > {threshold}')
    else:
        df['selected_gh'] = evaluate_binned_cut(
            df.gamma_prediction.to_numpy(), df.gamma_energy_prediction.to_numpy() * u.TeV, threshold, operator.ge
        )
        df_selected = df.query('selected_gh')

    pointing_icrs = SkyCoord(
        df_selected.pointing_ra.values * u.rad,
        df_selected.pointing_dec.values * u.rad,
        frame='icrs'
    )

    prediction_icrs = SkyCoord(
        df_selected.source_ra_prediction.values * u.rad, 
        df_selected.source_dec_prediction.values * u.rad, 
        frame='icrs'
    )

    theta, theta_off = calc_theta_off(
        source_coord=source,
        reco_coord=prediction_icrs,
        pointing_coord=pointing_icrs,
        n_off=n_offs,
    )

    # generate df containing corresponding energies etc for theta_off
    df_selected5 = df_selected
    for i in range(n_offs-1):
        df_selected5 = df_selected5.append(df_selected)

    return df_selected, ontime, theta, df_selected5, theta_off