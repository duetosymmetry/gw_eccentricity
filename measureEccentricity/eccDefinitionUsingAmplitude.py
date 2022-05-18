"""
Find peaks and troughs using Amplitude.

Part of Eccentricity Definition project.
Md Arif Shaikh, Mar 28, 2022
"""
from .eccDefinition import eccDefinition
from scipy.signal import find_peaks
from .utils import check_kwargs_and_set_defaults
from .plot_settings import use_fancy_plotsettings, colorsDict
import matplotlib.pyplot as plt
import numpy as np


class eccDefinitionUsingAmplitude(eccDefinition):
    """Define eccentricity by finding extrema location from amplitude."""

    def __init__(self, *args, **kwargs):
        """Init for eccDefinitionUsingAmplitude class.

        parameters:
        ----------
        dataDict: Dictionary containing the waveform data.
        """
        super().__init__(*args, **kwargs)
        self.data_for_finding_extrema = self.get_data_for_finding_extrema()

        # Sanity check extrema_finding_kwargs and set default values
        self.extrema_finding_kwargs = check_kwargs_and_set_defaults(
            self.extra_kwargs['extrema_finding_kwargs'],
            self.get_default_extrema_finding_kwargs(),
            "extrema_finding_kwargs")

    def get_default_extrema_finding_kwargs(self):
        """Defaults for extrema_finding_kwargs."""
        # TODO: Set width more smartly
        default_extrema_finding_kwargs = {
            "height": None,
            "threshold": None,
            "distance": None,
            "prominence": None,
            "width": 50,
            "wlen": None,
            "rel_height": 0.5,
            "plateau_size": None}
        return default_extrema_finding_kwargs

    def get_data_for_finding_extrema(self):
        """Get data to be used for finding extrema location.

        In the derived classes, one need to override this function
        to return the appropriate data that is to be used. For example,
        in residual amplitude method, this function would return
        residual amp22, whereas for frequency method, it would
        return omega22 and so on.
        """
        return self.amp22

    def find_extrema(self, extrema_type="maxima"):
        """Find the extrema in the amp22.

        parameters:
        -----------
        extrema_type: either maxima, peaks, minima or troughs
        extrema_finding_kwargs: Dictionary of arguments to be passed to the
        peak finding function. Here we use scipy.signal.find_peaks for finding
        peaks. Hence the arguments are those that are allowed in that function

        returns:
        ------
        array of positions of extrema.
        """
        if extrema_type in ["maxima", "peaks"]:
            sign = 1
        elif extrema_type in ["minima", "troughs"]:
            sign = - 1
        else:
            raise Exception("`extrema_type` must be one of ['maxima', "
                            "'minima', 'peaks', 'troughs']")

        return find_peaks(
            sign * self.data_for_finding_extrema,
            **self.extrema_finding_kwargs)[0]

    def make_diagnostic_plots(self, **kwargs):
        """Make dignostic plots for the eccDefinition method.

        We plot differenct quantities to asses how well our eccentricity
        measurment method is working. This could be seen as a diagnostic tool
        to check an implemented method.

        We plot the following quantities
        - The eccentricity vs vs time
        - decc/dt vs time, this is to test the monotonicity of eccentricity as
          a function of time
        - mean anomaly vs time
        - omega_22 vs time with the peaks and troughs shown. This would show
          if the method is missing any peaks/troughs or selecting one which is
          not a peak/trough
        - deltaPhi_orb(i)/deltaPhi_orb(i-1), where deltaPhi_orb is the
          change in orbital phase from the previous extrema to the ith extrema.
          This helps to look for missing extrema, as there will be a drastic
          (roughly factor of 2) change in deltaPhi_orb(i) if there is a missing
          extrema, and the ratio will go from ~1 to ~2.

        Additionally, we plot the following if data for zero eccentricity is
        provided
        - residual amp22 vs time with the location of peaks and troughs shown.
        - residual omega22 vs time with the location of peaks and troughs
          shown.
        These two plots with further help in understanding any unwanted feature
        in the measured eccentricity vs time plot. For example, non smoothness
        the residual omega22 would indicate that the data in omega22 is not
        good which might be causing glitches in the measured eccentricity plot.
        """
        nrows = 7 if "hlm_zeroecc" in self.dataDict else 5
        figsize = (12, 4 * nrows)
        default_kwargs = {"nrows": nrows,
                          "figsize": figsize}
        for key in default_kwargs:
            if key not in kwargs:
                kwargs.update({key: default_kwargs[key]})
        use_fancy_plotsettings()
        fig, ax = plt.subplots(**kwargs)
        self.plot_measured_ecc(fig, ax[0])
        self.plot_decc_dt(fig, ax[1])
        self.plot_mean_ano(fig, ax[2])
        self.plot_extrema_in_omega(fig, ax[3])
        self.plot_phase_diff_ratio_between_peaks(fig, ax[4])
        if "hlm_zeroecc" in self.dataDict:
            self.plot_residual_omega(fig, ax[5])
            self.plot_residual_amp(fig, ax[6])
        fig.tight_layout()
        return fig, ax

    def plot_measured_ecc(self, fig=None, ax=None, **kwargs):
        """Plot measured ecc as function of time."""
        if fig is None or ax is None:
            figNew, axNew = plt.subplots()
        else:
            axNew = ax
        default_kwargs = {"c": colorsDict["default"]}
        for key in default_kwargs:
            if key not in kwargs:
                kwargs.update({key: default_kwargs[key]})
        axNew.plot(self.tref_out, self.ecc_ref, **kwargs)
        axNew.set_xlabel("time")
        axNew.set_ylabel("eccentricity")
        axNew.grid()
        if fig is None or ax is None:
            return figNew, axNew
        else:
            return axNew

    def plot_decc_dt(self, fig=None, ax=None, **kwargs):
        """Plot decc_dt as function of time to check monotonicity.

        If decc_dt becomes positive, ecc(t) is not monotonically decreasing.
        """
        if fig is None or ax is None:
            figNew, axNew = plt.subplots()
        else:
            axNew = ax
        default_kwargs = {"c": colorsDict["default"]}
        for key in default_kwargs:
            if key not in kwargs:
                kwargs.update({key: default_kwargs[key]})
        axNew.plot(self.t_for_ecc_test, self.decc_dt, **kwargs)
        axNew.set_xlabel("time")
        axNew.set_ylabel(r"$de/dt$")
        axNew.grid()
        if fig is None or ax is None:
            return figNew, axNew
        else:
            return axNew

    def plot_mean_ano(self, fig=None, ax=None, **kwargs):
        """Plot measured mean anomaly as function of time."""
        if fig is None or ax is None:
            figNew, axNew = plt.subplots()
        else:
            axNew = ax
        axNew.plot(self.tref_out, self.mean_ano_ref,
                   c=colorsDict["default"], **kwargs)
        axNew.set_xlabel("time")
        axNew.set_ylabel("mean anomaly")
        axNew.grid()
        if fig is None or ax is None:
            return figNew, axNew
        else:
            return axNew

    def plot_extrema_in_omega(self, fig=None, ax=None, **kwargs):
        """Plot omega22, the locations of the apastrons and periastrons, and their corresponding interpolants.

        This would show if the method is missing any peaks/troughs or
        selecting one which is not a peak/trough.
        """
        if fig is None or ax is None:
            figNew, axNew = plt.subplots()
        else:
            axNew = ax
        axNew.plot(self.tref_out, self.omega_peak_at_tref_out,
                   c=colorsDict["periastron"], label=r"$\omega_{p}(t)$",
                   **kwargs)
        axNew.plot(self.tref_out, self.omega_trough_at_tref_out,
                   c=colorsDict["apastron"], label=r"$\omega_{a}(t)$",
                   **kwargs)
        # plot only upto merger to make the plot readable
        end = np.argmin(np.abs(self.t))
        axNew.plot(self.t[: end], self.omega22[: end],
                   c=colorsDict["default"], label=r"$\omega_{22}(t)$")
        axNew.plot(self.t[self.peaks_location],
                   self.omega22[self.peaks_location],
                   c=colorsDict["periastron"],
                   marker=".", ls="")
        axNew.plot(self.t[self.troughs_location],
                   self.omega22[self.troughs_location],
                   c=colorsDict["apastron"],
                   marker=".", ls="")
        axNew.set_xlabel("time")
        axNew.grid()
        axNew.set_ylabel(r"$M\omega_{22}(t)$")
        axNew.legend()
        if fig is None or ax is None:
            return figNew, axNew
        else:
            return axNew

    def plot_phase_diff_ratio_between_peaks(self, fig=None, ax=None, **kwargs):
        """Plot phase diff ratio between consecutive as function of time.

        Plots deltaPhi_orb(i)/deltaPhi_orb(i-1), where deltaPhi_orb is the
        change in orbital phase from the previous extrema to the ith extrema.
        This helps to look for missing extrema, as there will be a drastic
        (roughly factor of 2) change in deltaPhi_orb(i) if there is a missing
        extrema, and the ratio will go from ~1 to ~2.
        """
        if fig is None or ax is None:
            figNew, axNew = plt.subplots()
        else:
            axNew = ax
        tpeaks = self.t[self.peaks_location[1:]]
        axNew.plot(tpeaks[1:], self.orb_phase_diff_ratio_at_peaks[1:],
                   c=colorsDict["periastron"],
                   marker=".", label="Periastron phase diff ratio")
        ttroughs = self.t[self.troughs_location[1:]]
        axNew.plot(ttroughs[1:], self.orb_phase_diff_ratio_at_troughs[1:],
                   c=colorsDict["apastron"],
                   marker=".", label="Apastron phase diff ratio")
        axNew.set_xlabel("time")
        axNew.set_ylabel(r"$\Delta \Phi_{orb}[i] / \Delta \Phi_{orb}[i-1]$")
        axNew.grid()
        axNew.legend()
        if fig is None or ax is None:
            return figNew, axNew
        else:
            return axNew

    def plot_residual_omega(self, fig=None, ax=None, **kwargs):
        """Plot residual omega22, the locations of the apastrons and periastrons, and their corresponding interpolants.

        Useful to look for bad omega data near merger.
        We also throw away post merger before since it makes the plot
        unreadble.
        """
        if fig is None or ax is None:
            figNew, axNew = plt.subplots()
        else:
            axNew = ax
        # plot only upto merger to make the plot readable
        end = np.argmin(np.abs(self.t))
        axNew.plot(self.t[: end], self.res_omega22[:end], c=colorsDict["default"])
        axNew.plot(self.t[self.peaks_location],
                   self.res_omega22[self.peaks_location],
                   marker=".", ls="", label="Periastron",
                   c=colorsDict["periastron"])
        axNew.plot(self.t[self.troughs_location],
                   self.res_omega22[self.troughs_location],
                   marker=".", ls="", label="Apastron",
                   c=colorsDict["apastron"])
        axNew.set_xlabel("time")
        axNew.grid()
        axNew.set_ylabel(r"$\Delta\omega_{22}$")
        axNew.legend()
        if fig is None or ax is None:
            return figNew, axNew
        else:
            return axNew

    def plot_residual_amp(self, fig=None, ax=None, **kwargs):
        """Plot residual amp22, the locations of the apastrons and periastrons, and their corresponding interpolants."""
        if fig is None or ax is None:
            figNew, axNew = plt.subplots()
        else:
            axNew = ax
        axNew.plot(self.t, self.res_amp22, c=colorsDict["default"])
        axNew.plot(self.t[self.peaks_location],
                   self.res_amp22[self.peaks_location],
                   c=colorsDict["periastron"],
                   marker=".", ls="", label="Periastron")
        axNew.plot(self.t[self.troughs_location],
                   self.res_amp22[self.troughs_location],
                   c=colorsDict["apastron"],
                   marker=".", ls="", label="Apastron")
        axNew.set_xlabel("time")
        axNew.grid()
        axNew.set_ylabel(r"$\Delta A_{22}$")
        axNew.legend()
        if fig is None or ax is None:
            return figNew, axNew
        else:
            return axNew
