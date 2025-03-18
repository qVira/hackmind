using System;
using UnityEngine;

public class AbsoluteValueFilter : AbstractDataProvider {

    override public event Action<float[], double> OnDataReceived;

    [SerializeField]
    private AbstractDataProvider dataSource;

    private void Awake() {
        dataSource.OnDataReceived += DataSource_OnDataReceived;
    }

    private void DataSource_OnDataReceived(float[] inData, double timestamp) {
        float[] outData = new float[inData.Length];
        for(int i=0; i< inData.Length; i++) {            
            if (inData[i] > 0.5f) {
                outData[i] = (inData[i] - 0.5f) * 2f;
            } else if (inData[i] < 0.5f) {
                outData[i] = (0.5f - inData[i]) * 2f;
            } else {
                outData[i] = 0f;
            }
        }
        OnDataReceived?.Invoke(outData, timestamp);
    }
}
