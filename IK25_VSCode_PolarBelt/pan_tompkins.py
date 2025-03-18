import numpy as np
from scipy.signal import butter, filtfilt, iirnotch

class Pan_tompkins:
    """ Implementation of Pan Tompkins Algorithm.

    Noise cancellation (bandpass filter) -> Derivative step -> Squaring and integration.

    Params:
        data (array) : ECG data
        sampling rate (int)
    returns:
        Integrated signal (array) : This signal can be used to detect peaks

    """
    def __init__(self, data, sample_rate):
        self.data = data
        self.sample_rate = sample_rate

    def fit(self, normalized_cut_offs=None, butter_filter_order=2, padlen=150, window_size=None):
        ''' Fit the signal according to algorithm and returns integrated signal
        '''
        # 1. Noise cancellation using bandpass filter and notch filter
        self.filtered_BandPass = self.band_pass_filter(normalized_cut_offs, butter_filter_order, padlen)
        self.filtered_Notch = self.notch_filter(self.filtered_BandPass)

        # 2. Derivative filter to get slope of the QRS
        self.derviate_pass = self.derivative_filter()

        # 3. Squaring to enhance dominant peaks in QRS
        self.square_pass = self.squaring()

        # 4. To get info about QRS complex
        self.integrated_signal = self.moving_window_integration(window_size)

        return self.integrated_signal

    def band_pass_filter(self, normalized_cut_offs=None, butter_filter_order=2, padlen=150):
        ''' Band pass filter for Pan Tompkins algorithm with a bandpass setting of 5 to 20 Hz
        '''
        # Calculate Nyquist sample rate and cutoffs
        nyquist_sample_rate = self.sample_rate / 2

        # Calculate cutoffs
        if normalized_cut_offs is None:
            normalized_cut_offs = [5/nyquist_sample_rate, 15/nyquist_sample_rate]
        else:
            assert type(self.sample_rate) is list, "Cutoffs should be a list with [low, high] values"

        # Butter coefficients 
        b_coeff, a_coeff = butter(butter_filter_order, normalized_cut_offs, btype='bandpass')[:2]

        if len(self.data) <= padlen:
            padlen = len(self.data) - 1

        # Apply forward and backward filter
        filtered_BandPass = filtfilt(b_coeff, a_coeff, self.data, padlen=padlen)
        
        return filtered_BandPass

    def notch_filter(self, data, notch_freq=50.0, quality_factor=30.0):
        ''' Notch filter to remove powerline interference (50 Hz or 60 Hz)
        '''
        nyquist_freq = 0.5 * self.sample_rate
        norm_notch_freq = notch_freq / nyquist_freq
        b, a = iirnotch(norm_notch_freq, quality_factor)
        filtered_Notch = filtfilt(b, a, data)
        return filtered_Notch

    def derivative_filter(self):
        ''' Derivative filter
        '''
        # Apply differentiation
        derviate_pass = np.diff(self.filtered_Notch)
        return derviate_pass

    def squaring(self):
        ''' Squaring application on derivative filter output data
        '''
        # Apply squaring
        square_pass = self.derivative_filter() ** 2
        return square_pass 

    def moving_window_integration(self, window_size=None):
        ''' Moving average filter 
        '''
        if window_size is None:
            assert self.sample_rate is not None, "if window size is None, sampling rate should be given"
            window_size = int(0.08 * int(self.sample_rate))  # given in paper 150ms as a window size
        
        # Define integrated signal
        integrated_signal = np.zeros_like(self.squaring())

        # Cumulative sum of signal
        cumulative_sum = self.squaring().cumsum()

        # Estimation of area/ integral below the curve defines the data
        integrated_signal[window_size:] = (cumulative_sum[window_size:] - cumulative_sum[:-window_size]) / window_size
        integrated_signal[:window_size] = cumulative_sum[:window_size] / np.arange(1, window_size + 1)

        return integrated_signal

    def findpeaks(self, data, spacing=1, limit=None):
        """Detect peaks in data based on distance and height.
        
        Params:
            data (array): Input signal.
            spacing (int): Minimum number of samples between successive peaks.
            limit (float): Minimum height of peaks.
            
        Returns:
            array: Indices of peaks in the signal.
        """
        len_data = data.size
        x = np.zeros(len_data + 2 * spacing)
        x[:spacing] = data[0] - 1.e-6
        x[-spacing:] = data[-1] - 1.e-6
        x[spacing:spacing + len_data] = data
        peak_candidate = np.ones(len_data, dtype=bool)
        for s in range(1, spacing + 1):
            start = spacing - s
            h_b = x[start: start + len_data]  # before
            start = spacing
            h_c = x[start: start + len_data]  # central
            start = spacing + s
            h_a = x[start: start + len_data]  # after
            peak_candidate = peak_candidate & (h_c > h_b) & (h_c > h_a)  # keep points that are > than their neighbours
        ind = np.argwhere(peak_candidate).flatten()  # find indices of peak candidates
        if limit is not None:
            ind = ind[data[ind] > limit]  # filter out peaks below the limit
        return ind