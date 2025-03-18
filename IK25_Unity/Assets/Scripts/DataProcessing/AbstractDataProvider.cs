using System;
using UnityEngine;

public abstract class AbstractDataProvider : MonoBehaviour {
    abstract public event Action<float[], double> OnDataReceived;
}