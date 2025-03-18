# Mind and Body UI Hackathon

## Requirements
* Laptop with Win 10 or newer, Bluetooth
* Git & Git LFS
* Python 3.10 or newer
* Visual Studio Code
* Unity HUB & Unity 6000.0.36f1 or newer

## Preparations
* Install all Software Requirements
* Check out this repository
* Pair & try to connect all three bluetooth devices with your laptop once. This is required for automatic future connections.

## Important Links

[GIT](https://git-scm.com) & [GIT LFS](https://git-lfs.com) \
[Unity Tutorials & Docs](https://learn.unity.com/tutorial/start-learning-unity) \
[Unity Game Object Life Cycle](https://docs.unity3d.com/6000.0/Documentation/Manual/execution-order.html) \
[Unity Asset Store - Free Assets](https://assetstore.unity.com/?free=true&orderBy=1) \
[IXR Suite Repository](https://github.com/Zanderlabs/IXR-Suite)

## Processed LSL Streams

### Muse
"BrainPower" {derivative value} \
"SpectralPower" {delta, theta, alpha, beta, gamma}

### Polar Belt
"HRV_HR_Measures" {Heart Rate BPM, Normalized RMSSD, LF/HF Ratio} \
"EMG_activity" {Processed Chest EMG}

## Quick Start

### Connect the PolarBelt
* Start up VSCode and open IK25_VSCode_PolarBelt
* Set up a virtual Python environment
* Set the bluetooth address of your PolarBelt device in main.Python[Line 24] and start the script.

### Connect the Muse
* Start ixr_suite.exe located in IK25_Unity\Assets\Plugins
* Click on connect

### Connect the MyoArmband
* Start PlayBionic.MyoArmbandBridge.exe located in IK25_Unity\Assets\Plugins\MyoArmbandAPI
* The armband will connect when starting the unity project

### Start the Unity project
* Add the project folder IK25_Unity to your Unity HUB (new -> from disc) and open it
* Select one of the sample scenes in Assets/scenes
* Press Play. You should see the charts moving and hear a heartbeat sound, indicating that all devcices are working.

# Good Luck!
