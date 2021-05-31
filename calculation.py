import operator
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


from pyirf.cuts import evaluate_binned_cut

from ctapipe.io import read_table
from ctapipe.coordinates import CameraFrame

from astropy.time import Time
from astropy.coordinates import SkyCoord, SkyOffsetFrame, AltAz, EarthLocation
import astropy.units as u
from astropy import table

from astropy.coordinates.erfa_astrom import erfa_astrom, ErfaAstromInterpolator


erfa_astrom.set(ErfaAstromInterpolator(10 * u.min))
location = EarthLocation.from_geodetic(-17.89139 * u.deg, 28.76139 * u.deg, 2184 * u.m)

pointing_key = '/dl1/monitoring/telescope/pointing/tel_001'
trigger_key = '/dl1/event/telescope/trigger'
source_pred_key = '/dl2/event/telescope/disp_prediction/tel_001'
gamma_pred_key = '/dl2/event/telescope/gamma_prediction/tel_001'
gamma_energy_pred_key = '/dl2/event/telescope/gamma_energy_prediction/tel_001'


def calc_ontime(time):
    time.sort()
    delta = np.diff(time)
    delta = delta[np.abs(delta) < 10]
    return len(time) * delta.mean() * u.s


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

    table_pointing = read_table(run, pointing_key)
    table_trigger = read_table(run, trigger_key)
    table_disp_pred = read_table(run, source_pred_key)
    table_gamma_pred = read_table(run, gamma_pred_key)
    table_gamma_energy_pred = read_table(run, gamma_energy_pred_key)

    interp_az = np.interp(table_trigger['time'].mjd, table_pointing['time'].mjd, table_pointing['azimuth'])
    interp_alt = np.interp(table_trigger['time'].mjd, table_pointing['time'].mjd, table_pointing['altitude'])

    columns = [
        table_disp_pred['obs_id'],
        table_disp_pred['event_id'],
        table_disp_pred['alt_prediction'],
        table_disp_pred['az_prediction'],
        table_disp_pred['disp_prediction'],
        table_gamma_pred['gamma_prediction'],
        table_gamma_energy_pred['gamma_energy_prediction']
    ]

    df = pd.DataFrame()
    df['time'] = table_trigger['time'].mjd
    df['azimuth'] = interp_az
    df['altitude'] = interp_alt
    for col in columns:
        df[col.name] = col

    t = Time(df.time, format='mjd', scale='tai')
    t.format = 'unix'
    ontime = calc_ontime(t.value).to(u.hour)

    if type(threshold) == float:
        df_selected = df.query(f'gamma_prediction > {threshold}')

    else:
        df['selected_gh'] = evaluate_binned_cut(
            df.gamma_prediction.to_numpy(), df.gamma_energy_prediction.to_numpy() * u.TeV, threshold, operator.ge
        )
        df_selected = df.query('selected_gh')

    t_selected = Time(df_selected.time, format='mjd', scale='tai')
    t_selected.format = 'unix'
    altaz = AltAz(obstime=t_selected, location=location)

    pointing_altaz = SkyCoord(
        alt=u.Quantity(df_selected.altitude.values, u.rad, copy=False),
        az=u.Quantity(df_selected.azimuth.values, u.rad, copy=False),
        frame=altaz,
    )
    prediction_altaz = SkyCoord(
        alt=u.Quantity(df_selected.alt_prediction.values, u.deg, copy=False),
        az=u.Quantity(df_selected.az_prediction.values, u.deg, copy=False),
        frame=altaz,
    )

    pointing_icrs = pointing_altaz.transform_to('icrs')
    prediction_icrs = prediction_altaz.transform_to('icrs')

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
