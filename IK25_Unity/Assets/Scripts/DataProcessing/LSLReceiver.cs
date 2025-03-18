using LSL;
using System;
using UnityEngine;

public class LSLReceiver : AbstractDataProvider
{
    override public event Action<float[], double> OnDataReceived;

    [SerializeField]
    private string StreamName = "DummyWorkload1";

    private StreamInfo[] streamInfos;
    private StreamInlet streamInlet;

    private int channelCount = 0;
    private float[] dataSample;    

    // Update is called once per frame
    void Update() {
        
        //Try to open Stream Inlet
        if (streamInlet == null) {
            streamInfos = LSL.LSL.resolve_stream("name", StreamName, 1, 0.0);
            if (streamInfos.Length > 0) {
                streamInlet = new StreamInlet(streamInfos[0]);
                channelCount = streamInlet.info().channel_count();
                streamInlet.open_stream();
                Debug.Log($"Connected to LSL stream '{StreamName}'");
            }
        }

        //If we have an inlet, receive data!
        if (streamInlet != null) {
            dataSample = new float[channelCount];
            double lastTimeStamp = streamInlet.pull_sample(dataSample, 0.0f);
            if (lastTimeStamp != 0.0) {
                //Process all available samples
                Process(dataSample, lastTimeStamp);
                while ((lastTimeStamp = streamInlet.pull_sample(dataSample, 0.0f)) != 0) {
                    Process(dataSample, lastTimeStamp);
                }
            }
        }

        void Process(float[] sample, double timestamp) {            
            OnDataReceived?.Invoke(sample, timestamp);
        }
    }
}
