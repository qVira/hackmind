using UnityEngine;

public class BurningSphere : MonoBehaviour
{
    [SerializeField]
    private AbstractDataProvider dataSource;

    [SerializeField]
    private int minParticles = 0;

    [SerializeField]
    private int maxParticles = 100;

    private ParticleSystem fireParticles;

    private void Awake() {
        if (dataSource != null) {
            dataSource.OnDataReceived += ReceiveDataSample;
        }

        fireParticles = GetComponentInChildren<ParticleSystem>();
        if (fireParticles == null) {
            Debug.LogError("ParticleSystem component not found in children!");
            return;
        }
    }

    private void OnDestroy() {
        if (dataSource != null) {
            dataSource.OnDataReceived -= ReceiveDataSample;
        }
    }

    private void ReceiveDataSample(float[] sample, double timestamp) {
        ParticleSystem.MainModule main = fireParticles.main;
        float normalizedVal = sample[0];
        main.maxParticles = (int) Mathf.Round(normalizedVal * maxParticles);
    }
}
