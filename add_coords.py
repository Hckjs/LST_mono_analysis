import pandas as pd
import tables as tb
import numpy as np
from ctapipe.io import read_table
from astropy.time import Time
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
import astropy.units as u
import click

from ctapipe.coordinates import CameraFrame
from astropy.coordinates.erfa_astrom import erfa_astrom, ErfaAstromInterpolator


erfa_astrom.set(ErfaAstromInterpolator(10 * u.min))
location = EarthLocation.from_geodetic(-17.89139 * u.deg, 28.76139 * u.deg, 2184 * u.m)

pointing_key = '/dl1/monitoring/telescope/pointing/tel_001'
trigger_key = '/dl1/event/telescope/trigger'
source_pred_key = '/dl2/event/telescope/disp_prediction/tel_001'
gamma_pred_key = '/dl2/event/telescope/gamma_prediction/tel_001'
gamma_energy_pred_key = '/dl2/event/telescope/gamma_energy_prediction/tel_001'

@click.command()
@click.argument('infile', type=click.Path(exists=True, dir_okay=False))
def main(infile):

    table_pointing = read_table(infile, pointing_key)
    table_trigger = read_table(infile, trigger_key)
    table_disp_pred = read_table(infile, source_pred_key)
    table_gamma_pred = read_table(infile, gamma_pred_key)
    table_gamma_energy_pred = read_table(infile, gamma_energy_pred_key)

    interp_az = np.interp(table_trigger['time'].mjd, table_pointing['time'].mjd, table_pointing['azimuth'])
    interp_alt = np.interp(table_trigger['time'].mjd, table_pointing['time'].mjd, table_pointing['altitude'])

    columns = [
        table_disp_pred['obs_id'],
        table_disp_pred['event_id'],
        table_disp_pred['source_x_prediction'],
        table_disp_pred['source_y_prediction'],
        table_disp_pred['disp_prediction'],
        table_gamma_pred['gamma_prediction'],
        table_gamma_energy_pred['gamma_energy_prediction']
    ]

    df = pd.DataFrame()
    df['time'] = table_trigger['time'].mjd
    for col in columns:
        df[col.name] = col

    df['azimuth'] = interp_az
    df['altitude'] = interp_alt

    # TODO: Exception für Sim-files hinzufügen
    obstime = Time(df.time, format='mjd', scale='tai')
    obstime.format = 'unix'

    altaz = AltAz(obstime=obstime, location=location)

    pointing = SkyCoord(
        alt=u.Quantity(df.altitude.values, u.rad, copy=False),
        az=u.Quantity(df.azimuth.values, u.rad, copy=False),
        frame=altaz,
    )

    camera_frame = CameraFrame(telescope_pointing=pointing, location=location, obstime=obstime, focal_length=28 * u.m)

    prediction_cam = SkyCoord(
        x=u.Quantity(df.source_x_prediction.values, u.m, copy=False),
        y=u.Quantity(df.source_y_prediction.values, u.m, copy=False),
        frame=camera_frame,
    )

    prediction_altaz = prediction_cam.transform_to(altaz)
    prediction_icrs = prediction_altaz.transform_to('icrs')
    pointing_icrs = pointing.transform_to('icrs')

    df['source_alt_prediction'] = prediction_altaz.alt.rad
    df['source_az_prediction'] = prediction_altaz.az.rad
    df['source_ra_prediction'] = prediction_icrs.ra.rad
    df['source_dec_prediction'] = prediction_icrs.dec.rad
    df['pointing_ra'] = pointing_icrs.ra.rad
    df['pointing_dec'] = pointing_icrs.dec.rad

    with tb.open_file(infile, mode='a') as file:
        file.remove_node('/dl2/event/telescope/tel_001', recursive=True)

    with pd.HDFStore(infile) as out_:
        out_.put(key='/dl2/event/telescope/tel_001', value=df, format='table', data_columns=True)

if __name__ == '__main__':
    main()