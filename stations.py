# Copyright Google Inc. 2017
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

import pandas as pd
import numpy as np


def deg2rad(degree):
    rad = degree * 2 * np.pi / 360
    return(rad)


def convert_coords(data):
    """
    Takes in the dataframe of all WSC stations
    and converts lat/lon/elevation to xyz for
    more accurate distance measurements between
    stations.
    """
    data['Latitude'].dropna(inplace=True)
    data['Longitude'].dropna(inplace=True)

    data['Latitude'] = data['Latitude'].astype(
        float)
    data['Longitude'] = data['Longitude'].astype(
        float)

    data['dec_deg_latlon'] = data[[
        'Latitude', 'Longitude']].values.tolist()

    # convert decimal degrees to utm and make new columns for UTM Northing and Easting
    data['utm_latlon'] = [utm.from_latlon(
        e[0], e[1]) for e in data['dec_deg_latlon']]

    data['utm_E'] = [e[0] for e in data['utm_latlon']]
    data['utm_N'] = [e[1] for e in data['utm_latlon']]

    xyz = pd.DataFrame()
    xyz['r'] = 6378137 + data['Elevation']

    xyz['x'] = xyz['r'] * \
        np.cos(data['Latitude'].apply(deg2rad)) * \
        np.cos(data['Longitude'].apply(deg2rad))
    xyz['y'] = xyz['r'] * \
        np.cos(data['Latitude'].apply(deg2rad)) * \
        np.sin(data['Longitude'].apply(deg2rad))
    xyz['z'] = xyz['r'] * \
        np.sin(data['Latitude'].apply(deg2rad)) * (1 - 1 / 298.257223563)

    data['xyz_coords'] = xyz[['x', 'y', 'z']].values.tolist()

    return data


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data/')

stations_df = pd.read_csv(DATA_DIR + 'WSC_Stations_Master.csv')

print(stations_df.columns.values)

# stations_df.dropna(axis=0, subset=['Gross Drainage Area (km2)'], inplace=True)

STATIONS_DF = stations_df.copy()  # convert_coords(stations_df)

STATIONS_DF['record_length'] = STATIONS_DF['Year To'] - \
    STATIONS_DF['Year From']

STATIONS = [tuple(x)
            for x in STATIONS_DF[['Station Number', 'Station Name']].values]
COORDS = [tuple(x)
          for x in STATIONS_DF[['Station Number', 'Latitude', 'Longitude']].values]

# da_subset = stations_df[['Station Number', 'Gross Drainage Area (km2)']]
DRAINAGE_AREAS = [tuple(x) for x in STATIONS_DF[[
    'Station Number', 'Gross Drainage Area (km2)']].values]

IDS_TO_NAMES = {k: '{}: {}'.format(k, v) for (k, v) in STATIONS}
NAMES_TO_IDS = {v: k for (k, v) in STATIONS}
IDS_AND_DAS = {k: v for (k, v) in DRAINAGE_AREAS}
IDS_AND_COORDS = {k: (lat, lon) for (k, lat, lon) in COORDS}
