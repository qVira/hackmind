using System;
using System.Threading;
using UnityEngine;

using PlayBionic.MyoArmbandAPI.Manager;
using PlayBionic.MyoArmbandAPI.Armband;
using System.Collections.Generic;


#if (UNITY_WSA_10_0 || UNITY_STANDALONE_WIN) && !UNITY_EDITOR
using PlayBionic.MyoArmbandAPI.UWP;
#endif

#if UNITY_EDITOR
using PlayBionic.MyoArmbandAPI.Windows;
#endif

/// <summary>
/// Manager that handles communications between the game and the Myo Armband.
/// Useful for fetching data from the armband and listening to device events.
/// </summary>
public class MyoArmbandReceiver : AbstractDataProvider
{
    [SerializeField] private string myoArmbandAddress = "D8C329309A2A";

    /// <summary>
    /// Currently connected armband.
    /// </summary>
    public MyoArmband Armband { get; private set; }

    /// <summary>
    /// Event that fires when new EMG data is received from the armband.
    /// </summary>        
    override public event Action<float[], double> OnDataReceived;

    /// <summary>
    /// Event that fires when the connection state of the armband changes.
    /// </summary>
    public event Action<EConnectionState> ArmbandStateChanged;

    /// <summary>
    /// Get the relative orientation of the armband accounted for the 
    /// world rotation of the screen.
    /// </summary>
    // This property was written by trial and error
    // It will return the fixed-for-Unity orientation quaternion
    // The raw data we receive from the API is highly inverted
    public Quaternion TrueArmbandOrientation
    {
        get
        {
            if (Armband == null) return Quaternion.identity;

            Quaternion orientation = Armband.ImuData.Orientation;
            orientation = new Quaternion(orientation.y, orientation.x, -orientation.z, orientation.w);

            orientation = Quaternion.Euler(Vector3.right * -90) * orientation;

            orientation = orientation * Quaternion.Euler(Vector3.right * 180);
            orientation = Quaternion.Euler(Vector3.up * -ArmbandYRotationOffset) * orientation;

            return orientation;
        }

    }

    /// <summary>
    /// Used for Y rotation calibration of the armband.
    /// Value loaded by <see cref="ProfileManager"/> on game start.
    /// </summary>
    public float ArmbandYRotationOffset { get; set; }

    /// <summary>
    /// Disconnect from the current armband.
    /// </summary>
    public void DisconnectFromArmband()
    {
        if (Armband != null)
        {
            Armband.SetSleepMode(ESleepMode.Normal);

            Armband.OnConnectionStateChanged -= Armband_OnConnectionStateChanged;
            Armband.OnEmgDataReceived -= Armband_OnEmgDataReceived;
            Armband.Disconnect();

            Armband = null;
            ArmbandStateChanged?.Invoke(EConnectionState.Disconnected);
        }
    }

    /// <summary>
    /// Initiate a bluetooth scan for available armbands, and connect to the first one that is available.
    /// If no armband was found, this method will call itself again.
    /// </summary>
    public void InitiateScan()
    {
        if (Armband == null)
        {
            Debug.Log("Scan for devices...");
            MyoArmbandManager.scanForDevices(10, DeviceFoundCallback, InitiateScan);
        }
    }

    private List<EmgDataSample> receivedSamples = new();
    private float cooldownReconnect;

    private void Awake()
    {
        if (!MyoArmbandManager.isInitialized())
        {
#if (UNITY_WSA_10_0 || UNITY_STANDALONE_WIN) && !UNITY_EDITOR
                MyoArmbandManager.initialize(new UWPAdapter());
#elif UNITY_EDITOR || UNITY_STANDALONE_WIN
            MyoArmbandManager.initialize(new WindowsAdapter(8085, "pb_myo_bridge"));
#endif
        }
    }

    private void Start()
    {
        if (myoArmbandAddress.Trim().Length > 0)
        {
            try
            {
                ulong address = ulong.Parse(myoArmbandAddress, System.Globalization.NumberStyles.HexNumber);
                DeviceScanResult device = new DeviceScanResult("Myo", address);
                ConnectToDevice(device);
            } catch (Exception) { }
        }
    }

    private void Update()
    {
        if (Armband != null)
        {

            if (Armband.ConnectionState == EConnectionState.Connected)
            {
                // The current orientation of the Armband. We use it to set the rotation of the transform this component is attached to
                transform.rotation = Armband.ImuData.Orientation;

                //Copy received samples from threadsafe object
                List<EmgDataSample> samples;
                lock (receivedSamples)
                {
                    samples = new(receivedSamples);
                    receivedSamples.Clear();
                }

                //Process samples
                foreach (EmgDataSample s in samples)
                {
                    //data is always of size 8 and ranges from -128 to 127 (signed byte)                
                    sbyte[] data = s.get();
                    float[] normalized = new float[8];
                    for (int i = 0; i < 8; i++)
                    {
                        normalized[i] = (data[i] + 128f) / 256f;
                        //normalized[i] = data[i];
                    }
                    OnDataReceived?.Invoke(normalized, Time.time);
                }
            } else if (Armband.ConnectionState == EConnectionState.Disconnected ||
                       Armband.ConnectionState == EConnectionState.Failed && cooldownReconnect <= 0)
            {

                cooldownReconnect = 5f;
                try
                {
                    ulong address = ulong.Parse(myoArmbandAddress, System.Globalization.NumberStyles.HexNumber);
                    DeviceScanResult device = new DeviceScanResult("Myo", address);
                    ConnectToDevice(device);
                } catch (Exception) { }
            }
        }

        if (cooldownReconnect > 0)
        {
            cooldownReconnect -= Time.deltaTime;
        }
    }

    private void OnApplicationQuit()
    {
        DisconnectFromArmband();

        if (MyoArmbandManager.isInitialized())
            MyoArmbandManager.shutDown();
    }

    private void DeviceFoundCallback(DeviceScanResult scanResult)
    {
        Debug.Log("Device found! '" + scanResult.DeviceName + "'");

        // We already connected to a device
        if (Armband != null)
        {
            return;
        }

        ConnectToDevice(scanResult);
    }

    public void ConnectToDevice(DeviceScanResult scanResult)
    {
        // Disconnect existing armband if exists
        if (Armband != null) DisconnectFromArmband();

        // Create an Armband based on the found device address
        Armband = MyoArmbandManager.createArmband(scanResult);

        // If the Armband is not connected yet (default case)
        if (Armband.ConnectionState != EConnectionState.Connected)
        {
            // Register to its connection state change listener
            Armband.OnConnectionStateChanged += Armband_OnConnectionStateChanged;
            // And connect
            Armband.Connect();

            Debug.Log("Connect...");
        }
    }

    private void Armband_OnConnectionStateChanged(EConnectionState connectionState)
    {
        try
        {
            ArmbandStateChanged?.Invoke(connectionState);

            // If the connection state changed to connected, we enable IMU (orientation data) and EMG (sensor data) streams
            if (connectionState == EConnectionState.Connected)
            {
                Armband.SetSleepMode(ESleepMode.NeverSleep);
                Armband.ImuMode = EImuMode.Filtered;
                Armband.EmgMode = EEmgMode.Filtered;
                Armband.OnEmgDataReceived += Armband_OnEmgDataReceived;

                //Armband.EmgResolution = EEmgResolution.x8;

                Debug.Log("Connected!");
            }

            if (connectionState == EConnectionState.Disconnected)
            {
                Debug.Log("Disconnected from device");
            }

        } catch (Exception e)
        {
            Debug.LogError(e);
        }
    }

    private void Armband_OnEmgDataReceived(EmgDataSample[] samples)
    {
        lock (receivedSamples)
        {
            receivedSamples.Add(samples[0]);
        }
    }
}