using UnityEngine;

/// <summary>
/// HeartBeat
/// 
/// Requires a component of type AudioSource attached to the same game object.
/// </summary>
[RequireComponent(typeof(AudioSource))]
public class HeartBeat : MonoBehaviour {

    [SerializeField]
    private AbstractDataProvider dataSource;

    private AudioSource audioSource;

    private float heartRate = 0f;
    private float lastPlay = 0f;

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
    /// Gets called once 
    /// </summary>
    private void Start() {
        audioSource = GetComponent<AudioSource>();
    }

    /// <summary>
    /// Gets called once per frame
    /// </summary>
    private void Update() {

        //No pulse -> abort
        if (heartRate == 0) {
            return;
        }

        //Add the time since the last Update() call
        lastPlay += Time.deltaTime;

        //If the sample is still playing -> abort
        if (audioSource.isPlaying) {
            return;
        }

        // Heart rate is in beats per minute. Calculate the duration between heart beats
        float secondsPerBeat = 60f / heartRate;

        // If we waited long enough, play the next sample
        if (lastPlay >= secondsPerBeat) {
            Debug.Log("Play");
            audioSource.Play();
            lastPlay = 0f;
        }
    }

    private void ReceiveDataSample(float[] sample, double timestamp) {
        // We expect the "HRV_HR_Measures" stream from the polaris belt with the format:
        // {Average Heart Rate BPM, HRV Score, LF/HF Ratio }
        // and use the first element
        if (sample.Length > 0) {
            heartRate = sample[0];
        }        
    }
}
