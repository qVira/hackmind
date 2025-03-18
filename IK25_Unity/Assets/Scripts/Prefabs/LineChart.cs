using NUnit.Framework;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public class LineChart : MonoBehaviour
{
    [SerializeField]
    private AbstractDataProvider dataSource;

    [SerializeField]
    private int dataChannel = 0;

    [SerializeField]
    private int sampleCount = 10;

    [SerializeField]
    private float yMin = 0f;

    [SerializeField]
    private float yMax = 6f;

    [SerializeField]
    private float xMin = 0f;

    [SerializeField]
    private float xMax = 10f;

    private LineRenderer lineRenderer;
    private Queue<float> samples;

    private void Awake() {        
        lineRenderer = GetComponentInChildren<LineRenderer>();
        if (lineRenderer == null) {
            Debug.LogError("LineRenderer component not found in children!");
            return;
        }

        samples = new Queue<float>(sampleCount);        

        if (dataSource != null) {
            dataSource.OnDataReceived += ReceiveDataSample;
        }
    }

    private void OnDestroy() {
        if (dataSource != null) {
            dataSource.OnDataReceived -= ReceiveDataSample;
        }
    }    

    private void ReceiveDataSample(float[] sample, double timestamp) {
        if (samples.Count == sampleCount) {
            samples.Dequeue();
        }
        samples.Enqueue(sample[dataChannel]);

        lineRenderer.positionCount = samples.Count;
        for (int i = samples.Count - 1; i >= 0; i--) {
            float yNormalized = samples.ElementAt(i);
            float xNormalized = (i * 1f) / sampleCount;            
            lineRenderer.SetPosition(i, new Vector3(xMin + xNormalized * xMax, yMin + yNormalized * yMax, 0f));
        }            
    }
}
