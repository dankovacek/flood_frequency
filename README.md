# Flood Frequency Explorer

An interactive application to explore the concept of uncertainty in flood estimation.

![](img/app_screenshot.png)

## Description

Estimating flood magnitude is common practice for hydrologists.  A typical method of estimating a return period flood uses the annual peak  instantaneous flow series as an input, fitting a statistical distribution to the data (typically GEV, LPIII, etc.) and then extrapolating beyond the data, where there is considerable uncertainty.

A dataset of sufficient length to capture the true distribution of annual  floods, and as such, practitioners often have very limited sample sizes to work with.  The samples are the invariably sensitive to sample variability.  Further, the fragile assumption of non-stationarity founds the methodology on soggy ground (nice).


## Getting Started

### Dependencies

This application is developed on Ubuntu 18.

Package requirements include:
* numpy
* pandas
* scipy
* [Bokeh](https://bokeh.pydata.org/en/latest/index.html)

### Installing

* Clone the repo from github

* install the required packages (listed above)

### Executing program

From the root directory, execute:
```
>bokeh serve .
```
Note the address that the local Bokeh server launches, indicated in the terminal.
Typically, the address is:
```
http://localhost:5006/flood_freq
```

## Help

Any advise for common problems or issues.
```
command to run if program contains helper info
```

## Authors

Contributors names and contact info

ex. Dan KOvacek
ex. [@postnostills](https://twitter.com/postnostills)

## Version History

* 0.1
    * Initial Release

## License

This project is licensed under the MIT License - see the LICENSE.md file for details

## Acknowledgments

Inspiration, code snippets, etc.
* [awesome-readme](https://github.com/matiassingers/awesome-readme)
