using UnityEngine;

public class BarChart3D : MonoBehaviour {    

    [SerializeField]
    private AbstractDataProvider dataSource;

    [SerializeField]
    private Transform[] innerBars;

    private void Awake() {
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
        for (int i=0; i<innerBars.Length; i++) {            
            if (i >= sample.Length) {
                //No Channel available for this bar -> set to zero
                //TODO: set bar to one and grey it out
                SetBarHeight(innerBars[i], 0);
                continue;
            }
            //Set Bar height from data sample
            SetBarHeight(innerBars[i], sample[i]);
        }
        float yVal = sample[0];                
    }

    private void SetBarHeight(Transform bar, float val) {
        Vector3 scale = bar.localScale;
        scale.y = val;
        bar.localScale = scale;

        Vector3 pos = bar.localPosition;
        pos.y = (1f - val) / 2f;
        bar.localPosition = -pos;
    }
}
