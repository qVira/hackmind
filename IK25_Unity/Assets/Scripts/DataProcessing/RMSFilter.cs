using System.Collections.Generic;
using UnityEngine;
using System;

namespace PlayBionic.MyoOsu.Management
{
    public class RMSFilter : AbstractDataProvider
    {
        override public event Action<float[], double> OnDataReceived;

        [SerializeField]
        private AbstractDataProvider dataSource;

        [SerializeField]
        private int maxSampleSize = 50;
        private List<float[]> dataSamples = new List<float[]>();        

        private void Awake() {
            if (dataSource != null) {
                dataSource.OnDataReceived += DataSource_OnDataReceived;
            }
        }

        private void DataSource_OnDataReceived(float[] data, double timestamp) {
            
            // Add new samples and remove old ones to make sure we have not more than 50 samples in our list!
            dataSamples.Add(data);
            if (dataSamples.Count > maxSampleSize)
            {
                dataSamples.RemoveRange(0, dataSamples.Count - maxSampleSize);
            }

            // TODO: Rewrite using functions - reduce clutter

            // Based on the collected samples we calculate the root median square for each sensor value            
            {                
                int arraySize = dataSamples[0].Length;
                float[] rmsValues = new float[arraySize];
                float[] tempValues = new float[arraySize];
                foreach (float[] sensorValues in dataSamples)
                {                    
                    for (int i = 0; i < arraySize; i++)
                    {
                        tempValues[i] += Mathf.Pow(sensorValues[i], 2);
                    }
                }
                for (int i = 0; i < 8; i++)
                {
                    rmsValues[i] = Mathf.Sqrt(tempValues[i] / dataSamples.Count);                    
                }

                OnDataReceived?.Invoke(rmsValues, timestamp);
            }
        }
    }
}
