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
    mask_diff = []

    while (not np.array_equal(mask_copy, mask_diff)):
        mask_diff = mask_copy
        outer_ring = camera_geom.neighbor_matrix_sparse.dot(mask_copy) ^ mask_copy
        inner_ring = camera_geom.neighbor_matrix_sparse.dot(outer_ring) & mask_copy

        pixels_to_add = np.array([])
        mask_ring = inner_ring.copy()
        for pixel in np.where(mask_ring)[0]:
            neighbors = camera_geom.neighbor_matrix_sparse[pixel].indices
            time_diff = np.abs(peak_time[neighbors] - peak_time[pixel])
            if sum(time_diff < config['time_limit']) >= config['min_number_neighbors']:
                pixels_to_add = np.append(pixels_to_add,
                                          neighbors[time_diff < config['time_limit']])

        mask_ring[pixels_to_add.astype(int)] = True
        mask_copy = (mask_copy | mask_ring)

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
