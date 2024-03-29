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
    data.loc[:, 'logQ'] = list(map(math.log, data[param]))

    data['Tr'] = (len(data) + 1) / \
        data['rank'].astype(int).round(1)

    data.sort_values(by='rank', inplace=True, ascending=False)

    return data 


def norm_ppf(x):
    if x == 1.0:
        x += 0.001
    return st.norm.ppf(1-(1/x))


def update_UI_text_output(n_years):
    ffa_info.text = """Mean of {} simulations of a sample size {} \n
    out of a total {} years of record.  \n
    Bands indicate 1 and 2 standard deviations from the mean, respectively.""".format(
        simulation_number_input.value, sample_size_input.value, n_years)

    error_info.text = ""


def run_ffa_simulation(data, target_param, n_simulations):
    # reference:
    # https://nbviewer.jupyter.org/github/demotu/BMC/blob/master/notebooks/CurveFitting.ipynb

    model = pd.DataFrame()
    model['Tr'] = np.logspace(-2, 3, 500)
    model.set_index('Tr', inplace=True)
   
    model['z'] = list(map(norm_ppf, model.index.values))

    for i in range(n_simulations):

        sample_set = data.sample(
            sample_size_input.value, replace=False)

        selection = calculate_Tr(sample_set, target_param)

        # log-pearson distribution
        log_skew = st.skew(np.log10(selection[target_param]))

        lp3 = 2 / log_skew * \
            (np.power((model['z'] - log_skew / 6) * log_skew / 6 + 1, 3) - 1)

        lp3_model = np.power(10, np.mean(
            np.log10(selection[target_param])) + lp3 * np.std(np.log10(selection[target_param])))

        model[i] = lp3_model
    return model


def update():
    station_name = station_name_input.value.split(':')[-1].strip()
    df = get_annual_inst_peaks(
        NAMES_TO_IDS[station_name])


    # set the target param to PEAK to extract peak annual values 
    target_param = 'PEAK'

    if len(df) < 2:
        error_info.text = "Error, insufficient data in record (n = {}).  Resetting to default.".format(
            len(df))
        station_name_input.value = IDS_TO_NAMES['08MH016']
        update()

    data = calculate_Tr(df, 'PEAK')
    data.sort_values('Tr', ascending=False, inplace=True)

    data['Mean'] = np.mean(data['PEAK'])

    n_years = len(data)
    print('number of years of data = {}'.format(n_years))
    print("")

    # prevent the sample size from exceeding the
    # length of record
    if n_years < sample_size_input.value:
        sample_size_input.value = n_years - 1


    # Run the FFA fit simulation on a sample of specified size
    ## number of times to run the simulation
    n_simulations = simulation_number_input.value

    time0 = time.time()
    model = run_ffa_simulation(data, target_param, n_simulations)
    time_end = time.time()
    print("Time for {:.0f} simulations = {:0.2f} s".format(
        n_simulations, time_end - time0))

    # plot the log-pearson fit to the entire dataset
    log_skew = st.skew(np.log10(data[target_param]))
    z_model = np.array(list(map(norm_ppf, model.index.values)))
    z_empirical = np.array(list(map(norm_ppf, data['Tr'])))

    lp3_model = 2 / log_skew * \
        (np.power((z_model - log_skew / 6) * log_skew / 6 + 1, 3) - 1)

    lp3_empirical = 2 / log_skew * \
        (np.power((z_empirical - log_skew/6)*log_skew/6 + 1, 3)-1)

    lp3_quantiles_model = np.power(10, np.mean(
        np.log10(data[target_param])) + lp3_model*np.std(np.log10(data[target_param])))

    lp3_quantiles_empirical = np.power(10, np.mean(
        np.log10(data[target_param])) + lp3_empirical*np.std(np.log10(data[target_param])))

    data['theoretical'] = lp3_quantiles_empirical

    data['empirical_cdf'] = data['rank'] / (len(data) + 1)

    # pearson_fit_params = st.pearson3.fit(np.log(data['PEAK']))

    # reverse the order for proper plotting on P-P plot
    data['theoretical_cdf'] = st.pearson3.cdf(z_empirical, skew=log_skew)[::-1]

    # update the peak flow data source
    peak_source.data = peak_source.from_df(data)
    data_flag_filter = data[~data['SYMBOL'].isin([None, ' '])]
    peak_flagged_source.data = peak_flagged_source.from_df(data_flag_filter)

    # plot the simulation error bounds
    mean_models = model.apply(lambda row: row.mean(), axis=1)
    stdev_models = model.apply(lambda row: row.std(), axis=1)

    simulation = {'Tr': model.index,
                  'lower_1_sigma': np.subtract(mean_models, stdev_models),
                  'upper_1_sigma': np.add(mean_models, stdev_models),
                  'lower_2_sigma': np.subtract(mean_models, 2*stdev_models),
                  'upper_2_sigma': np.add(mean_models, 2*stdev_models),
                  'mean': mean_models,
                  'lp3_model': lp3_quantiles_model
                  }    

    distribution_source.data = simulation
    
    update_UI_text_output(n_years)


def update_station(attr, old, new):
    update()


def update_n_simulations(attr, old, new):
    if new > 1000:
        simulation_number_input.value = 1000
        error_info.text = "Max simulation size is 500"
    update()


def update_simulation_sample_size(attr, old, new):
    update()


# configure Bokeh Inputs, data sources, and plots
autocomplete_station_names = list(STATIONS_DF['Station Name'])
peak_source = ColumnDataSource(data=dict())
peak_flagged_source = ColumnDataSource(data=dict())
distribution_source = ColumnDataSource(data=dict())
qq_source = ColumnDataSource(data=dict())


station_name_input = AutocompleteInput(
    completions=autocomplete_station_names, title='Enter Station Name (ALL CAPS)',
    value=IDS_TO_NAMES['08MH016'], min_characters=3)

simulation_number_input = Spinner(
    high=1000, low=1, step=1, value=50, title="Number of Simulations",
)

sample_size_input = Spinner(
    high=200, low=2, step=1, value=10, title="Sample Size for Simulations"
)

ffa_info = Div(
    text="Mean of {} simulations of a sample size {}.".format('x', 'y'))

error_info = Div(text="", style={'color': 'red'})

# callback for updating the plot based on a changes to inputs
station_name_input.on_change('value', update_station)
simulation_number_input.on_change('value', update_n_simulations)
sample_size_input.on_change(
    'value', update_simulation_sample_size)

update()

# widgets
ts_plot = figure(title="Annual Maximum Flood",
                 #   x_range=(0.9, 2E2),
                 #   x_axis_type='log',
                 width=800,
                 height=250,
                 output_backend="webgl")

ts_plot.xaxis.axis_label = "Year"
ts_plot.yaxis.axis_label = "Flow (m³/s)"
ts_plot.circle('YEAR', 'PEAK', source=peak_source, legend_label="Measured Data")
ts_plot.circle('YEAR', 'PEAK', source=peak_flagged_source, color="orange",
               legend_label="Measured Data (QA/QC Flag)")

ts_plot.line('YEAR', 'Mean', source=peak_source, color='red',
             legend_label='Mean Annual Max', line_dash='dashed')

ts_plot.legend.location = "top_left"
ts_plot.legend.click_policy = 'hide'

# create a plot for the Flood Frequency Values and style its properties
ffa_plot = figure(title="Flood Frequency Analysis Explorer",
                  x_range=(0.9, 2E2),
                  x_axis_type='log',
                  width=800,
                  height=500,
                  output_backend="webgl")

ffa_plot.xaxis.axis_label = "Return Period (Years)"
ffa_plot.yaxis.axis_label = "Flow (m³/s)"

ffa_plot.circle('Tr', 'PEAK', source=peak_source, legend_label="Measured Data")
ffa_plot.circle('Tr', 'PEAK', source=peak_flagged_source, color="orange",
                legend_label="Measured Data (QA/QC Flag)")
ffa_plot.line('Tr', 'lp3_model', color='red',
              source=distribution_source,
              legend_label='Log-Pearson3 (All Data)')

ffa_plot.line('Tr', 'mean', color='navy',
              line_dash='dashed',
              source=distribution_source,
              legend_label='Mean Simulation')


# plot the error bands as shaded areas
ffa_2_sigma_band = Band(base='Tr', lower='lower_2_sigma', upper='upper_2_sigma', level='underlay',
                        fill_alpha=0.25, fill_color='#1c9099',
                        source=distribution_source)
ffa_1_sigma_band = Band(base='Tr', lower='lower_1_sigma', upper='upper_1_sigma', level='underlay',
                        fill_alpha=0.65, fill_color='#a6bddb', 
                        source=distribution_source)

ffa_plot.add_layout(ffa_2_sigma_band)
ffa_plot.add_layout(ffa_1_sigma_band)

ffa_plot.legend.location = "top_left"
ffa_plot.legend.click_policy = "hide"

# prepare a Q-Q plot
qq_plot = figure(title="Q-Q Plot",
                 width=400,
                 height=300,
                 output_backend="webgl")

qq_plot.xaxis.axis_label = "Empirical"
qq_plot.yaxis.axis_label = "Theoretical"

qq_plot.circle('PEAK', 'theoretical', source=peak_source)
qq_plot.line('PEAK', 'PEAK', source=peak_source, legend_label='1:1',
             line_dash='dashed', color='green')

qq_plot.legend.location = 'top_left'

# prepare a P-P plot
pp_plot = figure(title="P-P Plot",
                 width=400,
                 height=300,
                 output_backend="webgl")

pp_plot.xaxis.axis_label = "Empirical"
pp_plot.yaxis.axis_label = "Theoretical"

pp_plot.circle('empirical_cdf', 'theoretical_cdf', source=peak_source)
pp_plot.line('empirical_cdf', 'empirical_cdf', source=peak_source, legend_label='1:1',
             line_dash='dashed', color='green')

pp_plot.legend.location = 'top_left'

# create a page layout
layout = column(station_name_input,
                sample_size_input,
                simulation_number_input,
                ffa_info,
                error_info,
                ts_plot,
                ffa_plot,
                row(qq_plot, pp_plot)
                )

curdoc().add_root(layout)
