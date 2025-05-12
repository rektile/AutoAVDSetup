# AutoAVDSetup (WINDOWS)

This tool automates the process of rooting, installing frida-server and installing proxy tool on Android Virtual Devices (AVD), simplifying the setup for developers and security enthusiasts.

External tools that are used:
- rootAVD (https://github.com/newbit1/rootAVD)
- frida-server (https://github.com/frida/frida)
- android-proxy-toggle (https://github.com/theappbusiness/android-proxy-toggle)
- MagiskTrustUserCerts (https://github.com/NVISOsecurity/MagiskTrustUserCerts)


## prerequisites
- Android studio installed
- ADB added to your system path
- A running AVD 

## Installation
Clone the repository
```
git clone https://github.com/rektile/AutoAVDSetup.git
```

## Usage
Run the tool 
```
python main.py
```

## TODO

Support FAKEBOOTIMG argument for magisk version >= 26.x