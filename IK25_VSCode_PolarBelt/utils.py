import numpy as np
from scipy.signal import find_peaks
from scipy.interpolate import interp1d

def interpolate_ECG_peaks(raw_data,buffer,sample_rate,peaks):
    """
    interpolates peaks of ECG to reduce the impact on EMG analysis
    """
    
    # Define a window around the R-peak to remove (e.g., 20 ms before and after the peak)
    window_size = int(buffer / 1000 * sample_rate)  

    # Prepare a mask to mark R-peak regions
    mask = np.ones_like(raw_data, dtype=bool)

    # Mark the R-peak regions for removal
    for peak in peaks:
        mask[max(0, peak - window_size*3):min(len(raw_data), peak + window_size)] = False

    # Create a new array without R-peak regions
    cleaned_signal = np.copy(raw_data[mask])

    # Create a time array for the original and cleaned signal
    original_time = np.linspace(0, len(raw_data) / sample_rate, len(raw_data))
    cleaned_time = original_time[mask]

    # Interpolate to fill the gaps where R-peaks were removed
    interpolator = interp1d(cleaned_time, cleaned_signal, kind='linear', fill_value="extrapolate")
    interpolated_signal = interpolator(original_time)

    return interpolated_signal