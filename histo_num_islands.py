from matplotlib import pyplot as plt
import matplotlib.patches as mpatches
import astropy.units as u
import pandas as pd
import tables as tb
from ctapipe.instrument import CameraGeometry, SubarrayDescription
from ctapipe.visualization import CameraDisplay
from ctapipe.image import toymodel, tailcuts_clean, dilate
import numpy as np
import glob


def main():
    obs_paths = glob.glob('/fefs/aswg/workspace/jonas.hackfeld/masterarbeit/obs/crab/20201121/tailcuts_8_4/dl1_dvr_LST-1.Run029*.h5')

    num_islands_all = np.array([])
    for path in obs_paths:
        with tb.open_file(path, mode='r') as file:
            para_table = file.root['/dl1/event/telescope/parameters/tel_001']
            ni = para_table.cols.morphology_num_islands[:]
            num_islands = ni[ni != -1]
            num_islands_all = np.concatenate(num_islands_all, num_islands)

    df = pd.DataFrame()
    df['num_islands'] = num_islands_all
    df.to_hdf('/fefs/aswg/workspace/jonas.hackfeld/masterarbeit/obs/crab/20201121/tailcuts_8_4/num_islands/num_islands.h5', key='num_i', mode='w')

if __name__ == "__main__":
    main()
