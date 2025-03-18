import asyncio
import aioconsole
import os
import sys
import threading
import time
import signal

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, welch
from collections import deque
from pylsl import StreamInfo, StreamOutlet, StreamInlet, resolve_byprop
from bleak import BleakScanner, BleakClient

from pan_tompkins import Pan_tompkins
from utils import interpolate_ECG_peaks

# -----------------------------------------------------------------------------------
# CONFIG
# If ADDRESS is empty, we scan for the Polar device. Otherwise, we use your MAC.
# -----------------------------------------------------------------------------------
# ADDRESS = ""  
ADDRESS = "A0:9E:1A:D4:51:BE" # for ID C0684525
STREAMNAME = "PolarBand"

# LSL data-processing config
compute_rate = 10.0  # Hz
plot_length = 10  # seconds
EMG_average_window_duration = 1.0  # seconds
lf_band = (0.04, 0.15)
hf_band = (0.15, 0.4)
frequency_analysis_buffer_duration = 60  # seconds

# -----------------------------------------------------------------------------------
# POLAR UUIDS
# -----------------------------------------------------------------------------------
MODEL_NBR_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
MANUFACTURER_NAME_UUID = "00002a29-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
PMD_CONTROL = "FB005C81-02E7-F387-1CAD-8ACD2D8DF0C8"
PMD_DATA = "FB005C82-02E7-F387-1CAD-8ACD2D8DF0C8"
ECG_WRITE = bytearray([0x02, 0x00, 0x00, 0x01, 0x82, 0x00, 0x01, 0x01, 0x0E, 0x00])
ECG_SAMPLING_FREQ = 130

OUTLET = None  # Will be our ECG data outlet

# -----------------------------------------------------------------------------------
# LSL STREAM SETUP
# -----------------------------------------------------------------------------------
def StartStream(stream_name):
    info = StreamInfo(stream_name, 'ECG', 1, ECG_SAMPLING_FREQ, 'float32', 'myuid2424')
    info.desc().append_child_value("manufacturer", "Polar")
    channels = info.desc().append_child("channels")
    for c in ["ECG"]:
        channels.append_child("channel") \
            .append_child_value("name", c) \
            .append_child_value("unit", "microvolts") \
            .append_child_value("type", "ECG")
    return StreamOutlet(info)

def convert_array_to_signed_int(data, offset, length):
    return int.from_bytes(data[offset: offset + length], byteorder="little", signed=True)

# -----------------------------------------------------------------------------------
# NOTIFICATION CALLBACK - push samples to LSL
# -----------------------------------------------------------------------------------
def data_conv(sender, data: bytearray):
    if data and data[0] == 0x00:
        step = 3
        samples = data[10:]
        offset = 0
        ecg = []
        while offset < len(samples):
            ecg.append(convert_array_to_signed_int(samples, offset, step))
            offset += step
        stamp = time.time()  # or pylsl.local_clock()
        OUTLET.push_chunk(ecg, stamp)

# -----------------------------------------------------------------------------------
# DATA-PROCESSING LOOP
# This listens for the ECG LSL stream, applies filtering and Pan-Tompkins, then creates EMG derivative streams, etc.
# -----------------------------------------------------------------------------------
def data_processing_main():
    
    # from pan_tompkins import Pan_tompkins
    # from utils import interpolate_ECG_peaks  # Must be available in your environment
    
    compute_rate = 10.0
    plot_length = 10
    EMG_average_window_duration = 1
    lf_band = (0.04, 0.15)
    hf_band = (0.15, 0.4)
    frequency_analysis_buffer_duration = 60
    
    print("Looking for an ECG stream...")
    streams = resolve_byprop('type', 'ECG')
    if not streams:
        raise RuntimeError("No ECG streams found.")

    inlet = StreamInlet(streams[0])
    info_inlet = inlet.info()
    channel_count = info_inlet.channel_count()
    print(f"Stream has {channel_count} channels.")

    # Just assume selected channel is 0 for ECG
    selected_channels = [0]
    selected_channel_count = len(selected_channels)
    print(f"Selected channels: {selected_channels}")

    info_outlet = StreamInfo(
        name='EMG_activity',
        type='EMG',
        channel_count=selected_channel_count,
        nominal_srate=info_inlet.nominal_srate(),
        channel_format='float32',
        source_id='emg_source'
    )
    outlet = StreamOutlet(info_outlet)

    hrv_outlet_info = StreamInfo(
        name='HRV_HR_Measures',
        type='ECG',
        channel_count=3,
        nominal_srate=compute_rate,
        channel_format='float32',
        source_id='hrv_hr_source'
    )
    hrv_outlet = StreamOutlet(hrv_outlet_info)

    plt.ion()
    fig, axes = plt.subplots(nrows=selected_channel_count, ncols=2, figsize=(10,3))
    axes = np.atleast_2d(axes)
    original_lines = []
    processed_lines = []
    peak_lines = []

    for i in range(selected_channel_count):
        original_line, = axes[i, 0].plot([], [], label=f'Original Channel {i+1}')
        original_lines.append(original_line)
        axes[i, 0].set_title(f"Original Channel {i+1}")
        axes[i, 0].set_xlabel("Time (s)")
        axes[i, 0].set_ylabel("Amplitude")
        axes[i, 0].legend(loc='upper right')
        
        print("ECG found. Adding R-peak lines.")
        average_heart_rate_bpm = 0
        peak_line, = axes[i, 0].plot([], [], 'ro', label=f'R-peaks (HR: {average_heart_rate_bpm:.2f} BPM)')
        peak_lines.append(peak_line)
        
        processed_line, = axes[i, 1].plot([], [], label=f'EMG Channel {i+1}', color='r')
        processed_lines.append(processed_line)
        axes[i, 1].set_title(f"EMG Channel {i+1}")
        axes[i, 1].set_xlabel("Time (s)")
        axes[i, 1].set_ylabel("EMG activity")
        axes[i, 1].legend(loc='upper right')

    sample_rate = int(inlet.info().nominal_srate())
    buffer_size = int(sample_rate * plot_length)
    samples_buffer = np.empty((channel_count, 0))
    timestamps_buffer = []
    ibi_buffer = deque(maxlen=int(frequency_analysis_buffer_duration * 5))

    nyquist = 0.5 * sample_rate
    lowcut = 40.0
    highcut = min(450.0, nyquist - 1)
    print(f"EMG Bandpass Filter: {lowcut} Hz - {highcut} Hz")
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(2, [low, high], btype='band')
    window_size = int(EMG_average_window_duration * sample_rate)
    window = np.ones(window_size) / window_size
    last_sent_timestamp = -np.inf

    def calculate_lf_hf_ratio_welch(peak_time_points, ibi_values, fs=4.0):
        from scipy.interpolate import interp1d
        if len(ibi_values) < 4:
            return 0, 0, 0
        nn_times = peak_time_points
        nn_intervals = np.array(ibi_values)
        interp_time = np.arange(nn_times[0], nn_times[-1], 1/fs)
        if len(nn_times) < 2:
            return 0, 0, 0
        try:
            interp_func = interp1d(nn_times, nn_intervals, kind='linear', fill_value='extrapolate')
            interp_nn = interp_func(interp_time)
        except:
            return 0, 0, 0
        interp_nn_detrended = interp_nn - np.mean(interp_nn)
        freqs, psd = welch(interp_nn_detrended, fs=fs, nperseg=128)
        lf_mask = (freqs >= lf_band[0]) & (freqs <= lf_band[1])
        hf_mask = (freqs >= hf_band[0]) & (freqs <= hf_band[1])
        lf_power = np.trapz(psd[lf_mask], freqs[lf_mask])
        hf_power = np.trapz(psd[hf_mask], freqs[hf_mask])
        lf_hf_ratio = lf_power / hf_power if hf_power != 0 else 0
        return lf_power, hf_power, lf_hf_ratio

    # Main loop reading from LSL and processing
    while True:
        samples, timestamps = inlet.pull_chunk()
        if len(samples) > 0:
            samples_array = np.array(samples).T
            samples_buffer = np.hstack((samples_buffer, samples_array))
            timestamps_buffer.extend(timestamps)

            if samples_buffer.shape[1] < 2 * sample_rate:
                continue

            if samples_buffer.shape[1] > buffer_size:
                excess = samples_buffer.shape[1] - buffer_size
                samples_buffer = samples_buffer[:, excess:]
                timestamps_buffer = timestamps_buffer[excess:]

            samples_buffer_selected = samples_buffer[selected_channels, :]

            processed_signals = []
            for channel_index in range(selected_channel_count):
                signal_1ch = samples_buffer_selected[channel_index]
                # Run Pan-Tompkins on the signal (user must have Pan_tompkins installed)
                pt_algorithm = Pan_tompkins(signal_1ch, sample_rate)
                processed_ecg = pt_algorithm.fit()
                peak_indices = pt_algorithm.findpeaks(
                    processed_ecg,
                    spacing=sample_rate // 10,
                    limit=np.mean(processed_ecg) + np.std(processed_ecg)
                )
                peak_time_points = [timestamps_buffer[idx] for idx in peak_indices]
                ibi_values = np.diff(peak_time_points)

                for ibi_val in ibi_values:
                    ibi_buffer.append(ibi_val)

                if len(ibi_values) > 1:
                    average_heart_rate_bpm = np.mean(60 / ibi_values)
                    diff_ibi = np.diff(ibi_values)
                    if len(diff_ibi) > 0:
                        rmssd = np.sqrt(np.mean(diff_ibi ** 2))
                    else:
                        rmssd = 0
                    epsilon = 1e-8
                    scaled_rmssd = rmssd * 1000
                    if scaled_rmssd > 0:
                        ln_rmssd = np.log(scaled_rmssd + epsilon)
                        hrv_score = (ln_rmssd / 6.5) * 100
                        hrv_score = max(0, min(hrv_score, 100))
                    else:
                        hrv_score = 0
                    if len(ibi_buffer) >= 4:
                        current_peak_time_points = []
                        cumulative_time = 0
                        for ibi in list(ibi_buffer):
                            cumulative_time += ibi
                            current_peak_time_points.append(cumulative_time)
                        lf_power, hf_power, lf_hf_ratio = calculate_lf_hf_ratio_welch(
                            current_peak_time_points,
                            list(ibi_buffer),
                            fs=4.0
                        )
                    else:
                        lf_power, hf_power, lf_hf_ratio = 0, 0, 0
                else:
                    average_heart_rate_bpm = 0
                    hrv_score = 0
                    lf_power, hf_power, lf_hf_ratio = 0, 0, 0

                peak_lines[channel_index].set_label(
                    f'R-peaks (HR: {average_heart_rate_bpm:.2f} BPM, HRV: {hrv_score:.2f}, LF/HF: {lf_hf_ratio:.2f})'
                )

                # Interpolate peaks
                signal_1ch = interpolate_ECG_peaks(signal_1ch, 25, sample_rate, peak_indices)

                hrv_outlet.push_sample([average_heart_rate_bpm, hrv_score, lf_hf_ratio])

                # EMG-like filtering
                filtered_signal = filtfilt(b, a, signal_1ch)
                rectified_signal = abs(filtered_signal)
                envelope_signal = np.convolve(rectified_signal, window, mode='full')[:len(rectified_signal)]
                processed_signals.append(envelope_signal)

            emg_data_to_send = np.array(processed_signals).T.astype('float32')
            new_data_indices = [i for i, t in enumerate(timestamps_buffer) if t > last_sent_timestamp]
            if new_data_indices:
                new_data = emg_data_to_send[new_data_indices, :]
                new_timestamps = [timestamps_buffer[i] for i in new_data_indices]
                outlet.push_chunk(new_data, new_timestamps)
                last_sent_timestamp = new_timestamps[-1]

            time_axis = np.linspace(-buffer_size / sample_rate, 0, len(timestamps_buffer))
            for i in range(selected_channel_count):
                original_lines[i].set_data(time_axis, samples_buffer_selected[i])

                # R-peak indices => relative time
                peak_indices = []
                # We recompute them each iteration. If you saved them, you can reuse
                # But let's be consistent with the above lines:
                pt_algorithm = Pan_tompkins(samples_buffer_selected[i], sample_rate)
                processed_ecg = pt_algorithm.fit()
                peak_indices = pt_algorithm.findpeaks(
                    processed_ecg,
                    spacing=sample_rate // 10,
                    limit=np.mean(processed_ecg) + np.std(processed_ecg)
                )
                peak_time_points = [timestamps_buffer[idx] for idx in peak_indices]
                relative_peak_time_points = [
                    time_axis[np.argmin(np.abs(np.array(timestamps_buffer) - t_peak))]
                    for t_peak in peak_time_points
                ]
                peak_lines[i].set_data(relative_peak_time_points, samples_buffer_selected[i][peak_indices])

                processed_lines[i].set_data(time_axis, processed_signals[i])
                axes[i, 0].relim()
                axes[i, 0].autoscale_view()
                axes[i, 0].set_xlim([-buffer_size / sample_rate, 0])

                axes[i, 1].relim()
                axes[i, 1].autoscale_view()
                axes[i, 1].set_xlim([(-buffer_size / sample_rate) + EMG_average_window_duration, 0])
                axes[i, 0].legend(loc='upper right')

            plt.draw()
            plt.pause(0.01)

        time.sleep(1.0 / compute_rate)


# -----------------------------------------------------------------------------------
# ASYNCHRONOUS TASK: BLE CONNECT AND START NOTIFY
# -----------------------------------------------------------------------------------
async def run(client):
    print("---------Looking for Device------------ ", flush=True)
    await client.is_connected()
    print("---------Device connected--------------", flush=True)

    model_number = await client.read_gatt_char(MODEL_NBR_UUID)
    print("Model Number: {0}".format("".join(map(chr, model_number))), flush=True)

    manufacturer_name = await client.read_gatt_char(MANUFACTURER_NAME_UUID)
    print("Manufacturer Name: {0}".format("".join(map(chr, manufacturer_name))), flush=True)

    battery_level = await client.read_gatt_char(BATTERY_LEVEL_UUID)
    print("Battery Level: {0}%".format(int(battery_level[0])), flush=True)

    await client.read_gatt_char(PMD_CONTROL)
    print("Collecting GATT data...", flush=True)

    await client.write_gatt_char(PMD_CONTROL, ECG_WRITE)
    print("Writing GATT data...", flush=True)

    await client.start_notify(PMD_DATA, data_conv)
    print("Collecting ECG data...", flush=True)

    await aioconsole.ainput('Running! Data stream to LSL is live. It will take a moment until data arrives! Press enter to quit...')
    await client.stop_notify(PMD_DATA)
    print("Stopping ECG data...", flush=True)
    print("[CLOSED] application closed.", flush=True)
    sys.exit(0)

# -----------------------------------------------------------------------------------
# MAIN ASYNC WRAPPER
# -----------------------------------------------------------------------------------
async def main():
    global OUTLET
    OUTLET = StartStream(STREAMNAME)

    final_address = ADDRESS
    if not final_address:
        print("Scanning for Polar device...")
        devices = await BleakScanner.discover()
        polar_device = None
        for d in devices:
            if d.name and "Polar" in d.name:
                polar_device = d
                break
        if not polar_device:
            print("No Polar device found. Exiting.")
            sys.exit(1)
        final_address = polar_device.address
        print(f"Found Polar device: {polar_device.name} ({final_address})")
    else:
        print(f"Using specified MACADDRESS: {final_address}", flush=True)

    # Start data-processing as a separate thread so it won't block BLE
    processing_thread = threading.Thread(target=data_processing_main, daemon=True)
    processing_thread.start()

    try:
        print("Trying to connect to bluetooth Polarbelt H10 client...")
        async with BleakClient(final_address) as client:
            await run(client)
    except:
        print("Failed to connect to the device!")
        pass

# -----------------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------------
if __name__ == "__main__":
    os.environ["PYTHONASYNCIODEBUG"] = "1"

    # Gracefully handle Ctrl+C
    def handle_sigint(signum, frame):
        print("Received Ctrl+C, exiting.")
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_sigint)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
