import click
import sys

from tqdm import tqdm
import matplotlib.pyplot as plt
import astropy.units as u
import tables as tb
import numpy as np

from algorithms import DataVolumeReduction
from ctapipe.image import (
    tailcuts_clean,
    dilate
)
from ctapipe.visualization import CameraDisplay
from ctapipe.instrument import SubarrayDescription
from ctapipe.image import tailcuts_clean
from ctapipe.containers import (
    ArrayEventContainer,
    ImageParametersContainer,
    IntensityStatisticsContainer,
    PeakTimeStatisticsContainer,
    TimingParametersContainer,
)
from ctapipe.core import QualityQuery, TelescopeComponent
from ctapipe.image.image_processor import ImageQualityQuery
from ctapipe.core.traits import List
from ctapipe.image import (
    concentration_parameters,
    descriptive_statistics,
    hillas_parameters,
    leakage_parameters,
    morphology_parameters,
    timing_parameters,
)


DEFAULT_IMAGE_PARAMETERS = ImageParametersContainer()
DEFAULT_TIMING_PARAMETERS = TimingParametersContainer()
DEFAULT_PEAKTIME_STATISTICS = PeakTimeStatisticsContainer()


#Config
config_dvr={
    'volume_reducer':'ptdvr',
    'picture_threshold_pe':10.0,
    'boundary_threshold_pe':5.0,
    'min_picture_neighbors':1,
    'keep_isolated_pixels':False,
    'n_end_dilates':1,
    'min_number_neighbors':2,
    'time_limit':1.,
    'sigma_thresh':2.5
}

config_cleaning={
    'picture_threshold_pe':10.0,
    'boundary_threshold_pe':5.0,
    'min_picture_neighbors':1,
    'keep_isolated_pixels':False
}

config_quality_criteria = [
    ("enough_pixels", "lambda im: np.count_nonzero(im) > 2"),
    ("enough_charge", "lambda im: im.sum() > 50"),
]

ped_len = 100

def parameterize_image(check_image, image, signal_pixels, geometry, peak_time=None):
    image_selected = image[signal_pixels]
    image_criteria = check_image(image_selected)

    if all(image_criteria):
        geom_selected = geometry[signal_pixels]

        hillas = hillas_parameters(geom=geom_selected, image=image_selected)
        leakage = leakage_parameters(
            geom=geometry, image=image, cleaning_mask=signal_pixels
        )
        concentration = concentration_parameters(
            geom=geom_selected, image=image_selected, hillas_parameters=hillas
        )
        morphology = morphology_parameters(geom=geometry, image_mask=signal_pixels)
        intensity_statistics = descriptive_statistics(
            image_selected, container_class=IntensityStatisticsContainer
        )

        if peak_time is not None:
            timing = timing_parameters(
                geom=geom_selected,
                image=image_selected,
                peak_time=peak_time[signal_pixels],
                hillas_parameters=hillas,
            )
            peak_time_statistics = descriptive_statistics(
                peak_time[signal_pixels],
                container_class=PeakTimeStatisticsContainer,
            )
        else:
            timing = DEFAULT_TIMING_PARAMETERS
            peak_time_statistics = DEFAULT_PEAKTIME_STATISTICS

        return ImageParametersContainer(
            hillas=hillas,
            timing=timing,
            leakage=leakage,
            morphology=morphology,
            concentration=concentration,
            intensity_statistics=intensity_statistics,
            peak_time_statistics=peak_time_statistics,
        )

    return DEFAULT_IMAGE_PARAMETERS

def get_pedestal_thresh(ped_images, sigma_thresh):
    ped_mean = np.average(ped_images, axis=0)
    ped_std = np.std(ped_images, axis=0)
    pedestal_thresh = ped_mean + sigma_thresh * ped_std

    return pedestal_thresh

def calc_first_pedestal_thresh(file, sigma_thresh, ped_len):
    event_type = file.root['/dl1/event/subarray/trigger'].cols.event_type
    images_nodepath = '/dl1/event/telescope/images/tel_001'
    ped_indizes = np.where(event_type[:] == 2)[0][:ped_len]
    ped_images = file.root[images_nodepath][ped_indizes]['image']
    pedestal_thresh = get_pedestal_thresh(ped_images, sigma_thresh)

    return  pedestal_thresh, ped_images


@click.command()
@click.argument('filename', type=click.Path(exists=True, dir_okay=False))
def main(filename):
    subarray = SubarrayDescription.from_hdf(filename)
    ped_counter = 0

    with tb.open_file(filename, mode='a') as output_file:
        camera_geom = subarray.tel[1].camera.geometry
        image_nodepath = '/dl1/event/telescope/images/tel_001'
        parameters_nodepath = '/dl1/event/telescope/parameters/tel_001'
        trigger_nodepath = '/dl1/event/subarray/trigger'
        image_table = output_file.root[image_nodepath]
        parameters_table = output_file.root[parameters_nodepath]

        pedestal_thresh, ped_images = calc_first_pedestal_thresh(output_file,
                                                                 config_dvr['sigma_thresh'],
                                                                 ped_len)

        check_image = ImageQualityQuery()
        check_image.quality_criteria = config_quality_criteria

        volume_reducer = DataVolumeReduction(camera_geom=camera_geom)

        for i, (row_image, row_parameters) in enumerate(
            tqdm(
                zip(image_table, parameters_table),
                desc="Processing",
                unit=" image"
            )
        ):
            image = row_image['image'].copy()
            peak_time = row_image['peak_time'].copy()

            if output_file.root[trigger_nodepath][i]['event_type'] == 2:
                if ped_counter < ped_len:
                    ped_counter += 1
                    continue
                else:
                    ped_images = np.delete(ped_images, 0, 0)
                    ped_images = np.vstack((ped_images, image))
                    pedestal_thresh = get_pedestal_thresh(ped_images,
                                                          config_dvr['sigma_thresh'])
                    continue

            if output_file.root[trigger_nodepath][i]['event_type'] != 32:
                continue
            
            config_dvr['picture_threshold_pe'] = np.maximum(
                config_cleaning['picture_threshold_pe'],
                pedestal_thresh
            )

            if config_dvr['volume_reducer'] == 'tcdvr':
                dvr_mask = volume_reducer.tailcuts_dvr(image, config_dvr)
            if config_dvr['volume_reducer'] == 'ptdvr':
                dvr_mask = volume_reducer.peak_time_dvr(image, peak_time, config_dvr)
            if config_dvr['volume_reducer'] == 'mixeddvr':
                dvr_mask = volume_reducer.mixed_dvr(image, peak_time, config_dvr)

            image[~dvr_mask] = 0
            peak_time[~dvr_mask] = 0

            cleaning_mask = tailcuts_clean(
                geom=camera_geom,
                image=image,
                picture_thresh=config_dvr['picture_threshold_pe'],
                boundary_thresh=config_cleaning['boundary_threshold_pe'],
                keep_isolated_pixels=config_cleaning['keep_isolated_pixels'],
                min_number_picture_neighbors=config_cleaning['min_picture_neighbors']
            )

            parameter_container = parameterize_image(
                check_image=check_image,
                image=image,
                signal_pixels=cleaning_mask,
                geometry=camera_geom,
                peak_time=peak_time
            )

            row_image['image'] = image
            row_image['peak_time'] = peak_time
            row_image['image_mask'] = cleaning_mask

            for container in parameter_container.values():
                for colname, value in container.items(add_prefix=True):
                    if colname in {'hillas_psi', 'hillas_phi'}:
                        row_parameters[colname] = np.rad2deg(u.Quantity(value).value)
                    else:
                        row_parameters[colname] = u.Quantity(value).value

            row_image.update()
            row_parameters.update()

        image_table.flush()
        parameters_table.flush()

if __name__ == '__main__':
    main()