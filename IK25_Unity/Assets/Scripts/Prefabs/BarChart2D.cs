using UnityEngine;

/// <summary>
/// An 8-channel bar chart to be used in a Canvas
/// </summary>
public class BarChart2D : MonoBehaviour {    

    [SerializeField]
    private AbstractDataProvider dataSource;

    [SerializeField]
    private RectTransform[] innerBars;

    private void Awake() {
        if (dataSource != null) {
            //Register an event handler for received data samples
            dataSource.OnDataReceived += ReceiveDataSample;
        }
    }

    private void OnDestroy() {
        if (dataSource != null) {
            //Unregister the event handler
            dataSource.OnDataReceived -= ReceiveDataSample;
        }
    }

    /// <summary>
    /// Receives data samples and adjust the height of the 8 bars
    /// </summary>
    /// <param name="sample"></param>
    /// <param name="timestamp"></param>
    private void ReceiveDataSample(float[] sample, double timestamp) {        
        for (int i=0; i<innerBars.Length; i++) {            
            if (i >= sample.Length) {
                //No Channel available for this bar -> set to zero                
                SetBarHeight(innerBars[i], 0);
                //TODO: set bar to one and grey it out
                continue;
            }
            //Set Bar height from data sample
            SetBarHeight(innerBars[i], sample[i]);
        }
        float yVal = sample[0];                
    }

    /// <summary>
    /// Set the height of the bar by adjusting the Y of the scale vector
    /// </summary>
    /// <param name="bar">Transform of the bar to manipulate</param>
    /// <param name="val">Must be in the interval [0, 1]</param>
    private void SetBarHeight(RectTransform bar, float val) {
        Vector3 scale = bar.localScale;
        scale.y = val;
        bar.localScale = scale;
    }
}
