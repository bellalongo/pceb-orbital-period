import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import sys


# Global variables
period_bool_list = []
best_period_list = []


"""
    Appends all lightcurves of the desired cadence
    Name:       append_lightcurves()
    Parameters:
                result: star lightkurve query result
                result_exposures: star lightkurve query exposures
                cadence: desired lightcurve cadence
    Returns:
            None: if no lightcurves are of the desired cadence
            combined_lightcurve: appended lightcurves
"""
def append_lightcurves(result, result_exposures, cadence):
    all_lightcurves = []

    # Get the data whose exposure is the desired cadence
    for i, exposure in enumerate(result_exposures):
        # Check to see if exposure matches cadence 
        if exposure.value == cadence:
            lightcurve = result[i].download().remove_nans().remove_outliers().normalize() - 1
            all_lightcurves.append(lightcurve)
    
    # Check if there are lightcurves
    if all_lightcurves:
        combined_lightcurve = all_lightcurves[0]
        # Iterate through all of the lightcurves
        for lc in all_lightcurves[1:]:
            combined_lightcurve = combined_lightcurve.append(lc)
    else:
        return None
    
    return combined_lightcurve  


"""
    Determines if the period at max power of a periodogram is real based off of standard deviation
    Name:       is_real_period()
    Parameters: 
                periodogram: periodogram of the lightcurve
    Returns:
                boolean: True if the period is real, False if not real
                period: period at max power
"""
def is_real_period(periodogram, period):
    # Remove NaNs from the periodogram
    nan_mask = ~np.isnan(periodogram.power)
    periodogram_power = periodogram.power[nan_mask]
    periodogram_period = periodogram.period[nan_mask].value
    
    # Calculate period at max power
    std_dev = np.std(periodogram_power)

    # Check if within 5 sigma range
    if (abs(period - np.median(periodogram_period)) > 5 * std_dev) or (abs(period - np.median(periodogram_period)) > 4 * std_dev):
        return True
    else:
        return False
    

"""
    Calculates the best bin value based off of the duration of the lightcurve
    Name:       find_bin_value()
    Parameters:
                lightcurve: current star's lightcurve
                num_bins: desired number of bins (best value is the cadence)
    Returns:
                bin_value: number of minutes for each bin
"""
def find_bin_value(lightcurve, num_bins):
    total_points = len(lightcurve.time.value)
    total_duration_mins = ((lightcurve.time.value[total_points - 1] - lightcurve.time.value[0]) * u.day).to(u.minute)
    bin_value = (total_duration_mins/num_bins).value
    return bin_value


"""
    Present a series of plots folded on the 'best' period candidates, allowing the user
    to select the best one
    Name:       select_period()
    Parameters:
                lightcurve: current star's lightcurve
                periodogram: current star's periodogram
                literature_period: pre-calculated period, if any 
    Returns:
"""
def select_period(lightcurve, periodogram, literature_period, cadence, star_name, star_imag):
    period = periodogram.period_at_max_power.value 
    is_real = is_real_period(periodogram, period)

    # Plot basics
    sns.set_style("darkgrid")
    sns.set_theme(rc={'axes.facecolor':'#F8F5F2'})
    fig, axs = plt.subplots(2, 2, figsize=(14, 8))
    plt.subplots_adjust(hspace=0.35)
    plt.suptitle(fr"Press the key corresponding with the best period candidate (1,2,3), if none are good, press 'n'", fontweight = 'bold')
    if is_real:
        fig.text(0.5, 0.928, r'Note: $P_{\text{orb, max}}$ is over 5 sigma, so MIGHT be real', ha='center', fontsize=12, style = 'italic')
    else:
        fig.text(0.5, 0.928, r'Note: $P_{\text{orb, max}}$ is under 5 sigma, so might NOT be real', ha='center', fontsize=12, style = 'italic')
    fig.text(0.5, 0.05, f'{star_name}', ha='center', fontsize=16, fontweight = 'bold')
    fig.text(0.5, 0.02, fr'$i_{{\text{{mag}}}}={star_imag}$', ha='center', fontsize=12, fontweight = 'bold')
    cid = fig.canvas.mpl_connect('key_press_event', lambda event: on_key(event, 'Period selection'))

    # Plot the periodogram 
    axs[0, 0].set_title('Periodogram', fontsize=12)
    axs[0, 0].set_xlabel(r'$P_{\text{orb}}$ (days)', fontsize=10)
    axs[0, 0].set_ylabel('Power', fontsize=10)
    axs[0, 0].plot(periodogram.period, periodogram.power, color = '#322820')
    if literature_period != 0.0: axs[0, 0].axvline(x=literature_period, color = '#DF2935', 
                        label = fr'Literature $P_{{\text{{orb}}}}={np.round(literature_period, 2)}$ days')
    axs[0, 0].axvline(x=period, color = '#D36135', ls = 'solid', lw = 2, 
                        label = fr'$P_{{\text{{orb, max}}}}={np.round(period, 2)}$ days')
    axs[0, 0].axvline(x=period/2, color = '#DD882C', ls = 'dashed', lw = 2, 
                        label = fr'$\frac{{1}}{{2}} \times P_{{\text{{orb, max}}}}={np.round(period/2, 2)}$ days')
    axs[0, 0].axvline(x=2*period, color = '#E3BE4F', ls = 'dashed', lw = 2, 
                        label = fr'$2 \times P_{{\text{{orb, max}}}}={np.round(2*period, 2)}$ days')
    axs[0, 0].set_xscale('log') 
    axs[0, 0].legend(loc = 'upper left')

    # Fold on period at 1/2 * max power
    phase_lightcurve = lightcurve.fold(period = period/2)
    bin_value = find_bin_value(phase_lightcurve, cadence)
    binned_lightcurve = phase_lightcurve.bin(bin_value*u.min) 
    axs[1, 0].set_title(r'$\mathbf{1}$: Folded on $\frac{1}{2} \times P_{\text{orb, max}}$', fontsize=12)
    axs[1, 0].set_xlabel('Phase', fontsize = 10)
    axs[1, 0].set_ylabel('Normalized Flux', fontsize = 10)
    axs[1, 0].vlines(binned_lightcurve.phase.value, 
                        binned_lightcurve.flux - binned_lightcurve.flux_err, 
                        binned_lightcurve.flux + binned_lightcurve.flux_err, 
                        color = '#DD882C', lw=2, label = fr'$\frac{{1}}{{2}} \times P_{{\text{{orb, max}}}}={np.round(period/2, 2)}$ days')
    axs[1,0].legend()
    
    # Fold on max power
    phase_lightcurve = lightcurve.fold(period = period)
    bin_value = find_bin_value(phase_lightcurve, cadence)
    binned_lightcurve = phase_lightcurve.bin(bin_value*u.min) 
    axs[0, 1].set_title(r'$\mathbf{2}$: Folded on $P_{\text{orb, max}}$', fontsize=12)
    axs[0, 1].set_xlabel('Phase', fontsize = 10)
    axs[0, 1].set_ylabel('Normalized Flux', fontsize = 10)
    axs[0, 1].vlines(binned_lightcurve.phase.value, 
                        binned_lightcurve.flux - binned_lightcurve.flux_err, 
                        binned_lightcurve.flux + binned_lightcurve.flux_err, 
                        color = '#D36135', lw=2, label = fr'$P_{{\text{{orb, max}}}}={np.round(period, 2)}$ days')
    axs[0,1].legend()
    
    # Fold on 2* max power
    phase_lightcurve = lightcurve.fold(period = 2*period)
    bin_value = find_bin_value(phase_lightcurve, cadence)
    binned_lightcurve = phase_lightcurve.bin(bin_value*u.min) 
    axs[1, 1].set_title(r'$\mathbf{3}$: Folded on $2 \times P_{\text{orb, max}}$', fontsize=12)
    axs[1, 1].set_xlabel('Phase', fontsize = 10)
    axs[1, 1].set_ylabel('Normalized Flux', fontsize = 10)
    axs[1, 1].vlines(binned_lightcurve.phase.value, 
                        binned_lightcurve.flux - binned_lightcurve.flux_err, 
                        binned_lightcurve.flux + binned_lightcurve.flux_err, 
                        color = '#E3BE4F', lw=2, label = fr'$2 \times P_{{\text{{orb, max}}}}={np.round(2*period, 2)}$ days')
    axs[1,1].legend()
    
    plt.show()

    # Check which plot was selected
    curr_index = len(best_period_list) - 1
    if best_period_list[curr_index] == '1':
        return period/2
    elif best_period_list[curr_index] == '2':
        return period
    elif best_period_list[curr_index] == '3':
        return 2*period
    else:
        return False  


"""
    Creates a sine wave based off of given parameters
    Name:       sine_wave()
    Parameters: 
                x: data points
                amplitude: desired amplitude
                frequency: desired frequency
                phase: desired phase
    Returns:
                a sine wave
"""
def sine_wave(x, amplitude, frequency, phase):
    return amplitude * np.sin((2 * np.pi * frequency * x) + phase)



"""
    Event function that determines if a key was clicked
    Name:       on_key()
    Parameters: 
                event: key press event
                purpose: either doppler or noise
    Returns:
                None
"""
def on_key(event, purpose):
    real_period_keys = {'y', 'n'}
    period_selection_keys = {'1', '2', '3', 'n'}

    if purpose == 'Period selection':
        if event.key not in period_selection_keys:
            sys.exit("Invalid key input, select '1', '2', '3', or 'n'")
        else:
            best_period_list.append(event.key)
            if event.key == 'n':
                print(f'None selected, loading next plot ... \n')
            else:
                print(f'Selected plot {event.key}')
            plt.close()
    elif purpose == 'Real period':
        if event.key not in real_period_keys:
            sys.exit("Invalid key input, select 'y' or 'n'")
        else:
            period_bool_list.append(event.key == 'y')
            print('Loading next plot ... \n')
            plt.close()
    else:
        sys.exit("Invalid purpose, select 'Period selection' or 'Real period'")