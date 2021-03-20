import numpy as np
from ctapipe.image import tailcuts_clean, dilate

def tailcuts(image, camera_geom, config):
    mask = tailcuts_clean(
        geom=camera_geom,
        image=image,
        picture_thresh=config['picture_threshold_pe'],
        boundary_thresh=config['boundary_threshold_pe'],
        keep_isolated_pixels=config['keep_isolated_pixels'],
        min_number_picture_neighbors=config['min_picture_neighbors']
    )
    return mask

def dilates_at_end(mask, camera_geom, config):
    mask_copy = mask.copy()
    for _ in range(config['n_end_dilates']):
        mask_copy = dilate(camera_geom, mask_copy)
    return mask_copy

def infect_pixel_charge(image, mask, camera_geom, config):
    mask_copy = mask.copy()
    pixels_above_boundary_thresh = (image >= config['boundary_threshold_pe'])
    mask_diff = []

    while not np.array_equal(mask_copy, mask_diff):
        mask_diff = mask_copy
        mask_copy = dilate(camera_geom, mask_copy) & pixels_above_boundary_thresh
    return mask_copy

def infect_peak_time(peak_time, mask, camera_geom, config):
    mask_copy = mask.copy()
    pixels_to_add = 1

    while (np.sum(pixels_to_add) != 0):
        outer_ring = camera_geom.neighbor_matrix_sparse.dot(mask_copy) ^ mask_copy
        inner_ring = camera_geom.neighbor_matrix_sparse.dot(outer_ring) & mask_copy
        
        time_diffs = np.abs(peak_time[inner_ring, None] - peak_time)
        valid_neighbors = (time_diffs < config['time_limit']) & camera_geom.neighbor_matrix[inner_ring] & outer_ring
        enough_neighbors = np.count_nonzero(valid_neighbors, axis=1) >= config['min_number_neighbors']
        pixels_to_add = valid_neighbors[enough_neighbors].any(axis=0)
        mask_copy = (mask_copy | pixels_to_add)

    return mask_copy

class DataVolumeReduction():
    def __init__(self, camera_geom):
        self.camera_geom = camera_geom

    def tailcuts_dvr(self, image, config):
        tc_mask = tailcuts(image, self.camera_geom, config)
        mask = infect_pixel_charge(image, tc_mask, self.camera_geom, config)
        mask = dilates_at_end(mask, self.camera_geom, config)

        return mask

    def peak_time_dvr(self, image, peak_time, config):
        tc_mask = tailcuts(image, self.camera_geom, config)
        mask = infect_peak_time(peak_time, tc_mask, self.camera_geom, config)
        mask = dilates_at_end(mask, self.camera_geom, config)

        return mask

    def mixed_dvr(self, image, peak_time, config):
        tc_mask = tailcuts(image, self.camera_geom, config)
        mask_peak_time = infect_peak_time(peak_time, tc_mask, self.camera_geom, config)
        mask_charge = infect_pixel_charge(image, tc_mask, self.camera_geom, config)
        mask = mask_peak_time | mask_charge
        mask = dilates_at_end(mask, self.camera_geom, config)

        return mask
