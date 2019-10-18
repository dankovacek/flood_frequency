import os
import math

import numpy as np
import pandas as pd
import time

import scipy.special
import scipy.stats as st

from multiprocessing import Pool

from bokeh.layouts import row, column
from bokeh.models import CustomJS, Slider, Band, Spinner
from bokeh.plotting import figure, curdoc, ColumnDataSource
from bokeh.models.widgets import AutocompleteInput, Div

from get_station_data import get_daily_UR, get_annual_inst_peaks

from stations import IDS_AND_DAS, STATIONS_DF, IDS_TO_NAMES, NAMES_TO_IDS

# Step 1: Get one (or all of interest) stations >= min_n year records (complete year)
#         from the master station list.

# min_n = 50

# min_50_yr_record_stns_all = STATIONS_DF[STATIONS_DF['record_length'] >= min_n]

# min_50_yr_record_stns = min_50_yr_record_stns_all[min_50_yr_record_stns_all['Province'] == 'BC']

# peak_results = {}

# for stn in min_50_yr_record_stns['Station Number']:
#     flood_df = get_annual_inst_peaks(stn)

#     if len(flood_df) >= 50:
#         peak_results[stn] = flood_df


def get_stats(data, param):
    mean = data[param].mean()
    var = np.var(data[param])
    stdev = data[param].std()
    skew = st.skew(data[param])
    return mean, var, stdev, skew


def calculate_Tr(data, param, correction_factor=None):
    if correction_factor is None:
        correction_factor = 1

    data['rank'] = data[param].rank(ascending=False, method='first')
    data.loc[:, 'logQ'] = map(math.log, data[param])

    # mean_Q, var_Q, stdev_Q, skew_Q = get_stats(data, param)

#     print('mean: {}, var: {}, stdev: {}, skew: {}'.format(
#         round(mean_Q, 2), round(var_Q, 2), round(stdev_Q, 2), round(skew_Q, 2)))
    data['Tr'] = (len(data) + 1) / \
        data['rank'].astype(int).round(1)
    data.sort_values(by='rank', inplace=True, ascending=False)

    return data  # , mean_Q, var_Q, stdev_Q, skew_Q


def norm_ppf(x):
    if x == 1.0:
        x += 0.001
    return st.norm.ppf(1-(1/x))


def update():
    station_name = station_name_input.value.split(':')[-1].strip()
    df = get_annual_inst_peaks(
        NAMES_TO_IDS[station_name])
    # df['DateTime'] = pd.to_datetime(
    #     (df.YEAR*10000+df.MONTH*100+df.DAY).apply(str), format='%Y-%m-%d')
    # df.set_index('DateTime', inplace=True)

    if len(df) < 2:
        error_info.text = "Error, insufficient data in record (n = {}).  Resetting to default.".format(
            len(df))
        station_name_input.value = IDS_TO_NAMES['08MH016']
        update()

    data = calculate_Tr(df, 'PEAK')
    data.sort_values('Tr', ascending=False, inplace=True)

    # update the peak flow data source
    peak_source.data = peak_source.from_df(data)

    # reference:
    # https://nbviewer.jupyter.org/github/demotu/BMC/blob/master/notebooks/CurveFitting.ipynb

    param = 'PEAK'

    n_years = len(data)

    if n_years < simulation_population_size_input.value:
        simulation_population_size_input.value = n_years - 1

    # number of times to run the simulation
    n_simulations = simulation_number_input.value

    model = pd.DataFrame()
    model['Tr'] = np.linspace(1.01, 200, 500)
    model.set_index('Tr', inplace=True)

    model['z'] = map(norm_ppf, model.index.values)

    time0 = time.time()

    times1, times2, times3, times4, = [], [], [], []

    for i in range(n_simulations):

        ts = time.time()

        samp = data.sample(
            simulation_population_size_input.value, replace=False)

        in_t = time.time()
        times1.append(in_t - ts)

        selection = calculate_Tr(samp, param)

        t2 = time.time()
        times2.append(t2 - in_t)

        # log-pearson distribution
        log_skew = st.skew(np.log10(selection[param]))

        t3 = time.time()
        times3.append(t3 - t2)

        lp3 = 2 / log_skew * \
            (np.power((model['z'] - log_skew / 6) * log_skew / 6 + 1, 3) - 1)

        t4 = time.time()
        times4.append(t4 - t3)

        lp3_model = np.power(10, np.mean(
            np.log10(selection[param])) + lp3 * np.std(np.log10(selection[param])))
        #   print(lp3_model)
        model[i] = lp3_model.values

    time_end = time.time()
    print("Time for {:.0f} simulations = {:0.2f} s".format(
        n_simulations, time_end - time0))
    # print("Avg. time for inner step 1 = {:0.4f} s".format(
    #     np.mean(times1)))
    # print("Avg. time for inner step 2 = {:0.4f} s".format(
    #     np.mean(times2)))
    # print("Avg. time for inner step 3 = {:0.4f} s".format(
    #     np.mean(times3)))
    # print("Avg. time for inner step 4 = {:0.4f} s".format(
    # np.mean(times4)))
    # plot the log-pearson fit to the entire dataset
    # log-pearson distribution
    log_skew = st.skew(np.log10(data[param]))
    # print(model.index.values)
    z = np.array(map(norm_ppf, model.index.values))
    lp3 = 2 / log_skew * (np.power((z - log_skew/6)*log_skew/6 + 1, 3)-1)
    lp3_model = np.power(10, np.mean(
        np.log10(data[param])) + lp3 * np.std(np.log10(data[param])))

    # plot the simulation error bounds
    mean_models = model.apply(lambda row: row.mean(), axis=1)
    stdev_models = model.apply(lambda row: row.std(), axis=1)

    simulation = {'Tr': model.index,
                  'lower_1_sigma': np.subtract(mean_models, stdev_models),
                  'upper_1_sigma': np.add(mean_models, stdev_models),
                  'lower_2_sigma': np.subtract(mean_models, 2*stdev_models),
                  'upper_2_sigma': np.add(mean_models, 2*stdev_models),
                  'mean': mean_models,
                  'lp3_model': lp3_model,
                  }

    distribution_source.data = simulation
    ffa_info.text = """Mean of {} simulations of a sample size {} \n
    out of a total {} years of record.  \n
    Bands indicate 1 and 2 standard deviations from the mean, respectively.""".format(
        n_simulations, simulation_population_size_input.value, n_years)

    error_info.text = ""


def update_station(attr, old, new):
    update()


def update_num_simulations(attr, old, new):
    update()


def update_simulation_sample_size(attr, old, new):
    update()
# configure Bokeh Inputs, data sources, and plots


autocomplete_station_names = list(STATIONS_DF['Station Name'])
peak_source = ColumnDataSource(data=dict())
distribution_source = ColumnDataSource(data=dict())

station_name_input = AutocompleteInput(
    completions=autocomplete_station_names, title='Enter Station Name (ALL CAPS)',
    value=IDS_TO_NAMES['08MH016'], min_characters=3)

simulation_number_input = Spinner(
    high=200, low=1, step=1, value=50, title="Number of Simulations",
)

simulation_population_size_input = Spinner(
    high=200, low=2, step=1, value=10, title="Sample Size for Simulations"
)

ffa_info = Div(
    text="Mean of {} simulations of a sample size {}.".format('x', 'y'))

error_info = Div(text="", style={'color': 'red'})

# callback for updating the plot based on a change to the input station
station_name_input.on_change('value', update_station)
simulation_number_input.on_change('value', update_num_simulations)
simulation_population_size_input.on_change(
    'value', update_simulation_sample_size)

update()

# widgets

# create a plot and style its properties
ffa_plot = figure(title="Flood Frequency Analysis Explorer",
                  x_range=(0.9, 2E2),
                  x_axis_type='log',
                  width=800,
                  height=600)

ffa_plot.xaxis.axis_label = "Return Period (Years)"
ffa_plot.yaxis.axis_label = "Flow (m³/s)"

ffa_plot.circle('Tr', 'PEAK', source=peak_source)
ffa_plot.line('Tr', 'lp3_model', color='red',
              source=distribution_source,
              legend='Log-Pearson3 (All Data)')

ffa_plot.line('Tr', 'mean', color='navy',
              line_dash='dashed',
              source=distribution_source,
              legend='Mean Simulation')

# plot the error bands as shaded areas
ffa_2_sigma_band = Band(base='Tr', lower='lower_2_sigma', upper='upper_2_sigma', level='underlay',
                        fill_alpha=0.25, fill_color='#1c9099', source=distribution_source)
ffa_1_sigma_band = Band(base='Tr', lower='lower_1_sigma', upper='upper_1_sigma', level='underlay',
                        fill_alpha=0.65, fill_color='#a6bddb', source=distribution_source)

ffa_plot.add_layout(ffa_2_sigma_band)
ffa_plot.add_layout(ffa_1_sigma_band)

ffa_plot.legend.location = "top_left"
ffa_plot.legend.click_policy = "hide"

# ax.plot(all_models.index, all_models['mean'], color='blue', linestyle='dashed',
#         label='Mean for n= {} and {} simulations'.format(n_select, n_iterations))

# ax.fill_between(all_models.index, all_models['mean'] - all_models['stdev'], all_models['mean'] + all_models['stdev'],
#                 alpha=0.2, label='1 sigma', color='green')
# ax.fill_between(all_models.index, all_models['mean'] - 2*all_models['stdev'], all_models['mean'] + 2*all_models['stdev'],
#                 alpha=0.2, label='2 sigma', color='blue')


# format the figure
layout = column(station_name_input,
                simulation_population_size_input,
                simulation_number_input,
                ffa_info,
                error_info,
                ffa_plot)

curdoc().add_root(layout)
