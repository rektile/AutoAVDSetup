import os
import sys
import re

from src.utils import (
    getAVDLocations, doesAndroidVersionMatch, extractPathForRootAVD,
    runOSCommand, runInteractiveCommand, runADBCommand, isMagiskInstalled, isDeviceRooted,
    getLatestFridaServerReleases, downloadFileFromUrl, extractXZ,
    getLatestProxyToolRelease, extractZip, findFile, isProxyToolInstalled,
    getLatestMagiskTrustUserCertsRelease, downloadBurpCert, showHeader,
    clearScreen, hasAdb, isDeviceAttached, isActiveAVDPath, getRunningAPILevel,
    pushBusyboxToDevice, updateMagiskZip, is16KBPageSize,
)

EXTERNAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "external")


def prompt_choice(prompt_text, max_val):
    """Prompt the user for a numbered choice and validate it."""
    try:
        choice = int(input(prompt_text).strip())
    except ValueError:
        print("[!] That is not a valid option!")
        sys.exit(1)

    if choice < 1 or choice > max_val:
        print("[!] That is not a valid option!")
        sys.exit(1)

    return choice


def preflight_check():
    """Verify ADB is available and a device is attached."""
    if not hasAdb():
        print("[!] ADB not found in PATH. Please install Android SDK platform-tools.")
        sys.exit(1)
    if not isDeviceAttached():
        print("[!] No device attached. Start your AVD first.")
        sys.exit(1)


def rootDevice():
    print("[*] Listing installed AVDs.")

    paths = getAVDLocations()
    if not paths:
        print("[!] No AVD found!")
        sys.exit(1)

    for i, path in enumerate(paths):
        suffix = " (Running)" if isActiveAVDPath(path) else ""
        print(f"[-] {i + 1}) {path}{suffix}")

    print("[*] Make sure the AVD you want to root is running.")
    choice = prompt_choice("[?] Which AVD do you want to root: ", len(paths))

    chosenOption = paths[choice - 1]
    extractedPath = extractPathForRootAVD(chosenOption)

    # Determine if FAKEBOOTIMG is needed
    api_level = getRunningAPILevel()
    use_fakeboot = False

    if api_level >= 34:
        print(f"[*] API level {api_level} (Android 14+) detected — FAKEBOOTIMG is required (Magisk >= 26.x).")
        use_fakeboot = True
    else:
        fakeboot_input = input("[?] Use FAKEBOOTIMG? Recommended for Magisk >= 26.x (y/N): ").strip().lower()
        use_fakeboot = fakeboot_input in ("y", "yes")

    # Check for 16KB page size AVDs that need a newer Magisk
    if is16KBPageSize() or "ps16k" in chosenOption.lower():
        print("[*] 16KB page size AVD detected — bundled Magisk v26.4 is incompatible.")
        print("[*] Downloading latest Magisk with 16KB support...")
        if not updateMagiskZip(EXTERNAL_PATH):
            print("[!] Could not update Magisk. Try using a non-ps16k AVD image instead.")
            sys.exit(1)

    # Pre-push a compatible busybox to the device in case bundled ones don't work
    print("[*] Ensuring compatible busybox is available on device...")
    pushBusyboxToDevice(EXTERNAL_PATH)

    cmd = ["rootAVD.bat", extractedPath]
    if use_fakeboot:
        cmd.append("FAKEBOOTIMG")

    print("[*] Rooting device...")
    if use_fakeboot:
        print("[*] Using FAKEBOOTIMG — Magisk will launch to patch a fake boot.img.")
        print("[*] Follow the instructions in the terminal and on the AVD screen.")
    original_dir = os.getcwd()
    try:
        os.chdir(EXTERNAL_PATH)
        runInteractiveCommand(cmd)
    finally:
        os.chdir(original_dir)

    print("")
    print("[*] IMPORTANT: You must Cold Boot the AVD for changes to take effect.")
    print("    In Android Studio: Device Manager -> dropdown arrow -> Cold Boot Now")
    input("[*] Cold Boot the AVD and press ENTER when it's fully started...")

    # Install Magisk APK if available in the Apps folder
    apps_dir = os.path.join(EXTERNAL_PATH, "Apps")
    if os.path.isdir(apps_dir):
        for apk in os.listdir(apps_dir):
            if apk.lower().endswith(".apk"):
                apk_path = os.path.join(apps_dir, apk)
                print(f"[*] Installing {apk}...")
                runOSCommand(["adb", "install", "-r", "-d", apk_path])

    if not isMagiskInstalled():
        print("[!] Magisk app not found. Trying to install from Magisk.zip...")
        magisk_zip = os.path.join(EXTERNAL_PATH, "Magisk.zip")
        if os.path.exists(magisk_zip):
            runOSCommand(["adb", "install", "-r", "-d", magisk_zip])

    if isMagiskInstalled():
        print("[*] Magisk is installed.")
        input("[*] Open Magisk app on the AVD. If it asks for additional setup, complete it and press ENTER.")
    else:
        print("[!] Magisk app could not be installed automatically.")
        input("[*] Manually install Magisk and press ENTER.")

    print("[*] Make sure to accept root permissions on AVD")

    if isDeviceRooted():
        print("[*] Device was rooted successfully.")
    else:
        print("[!] Failed to root device!")
        sys.exit(1)


def installFridaServer():
    if not isDeviceRooted():
        print("[!] AVD is not rooted!")
        sys.exit(1)

    fridaInfo = getLatestFridaServerReleases()
    if "name" not in fridaInfo:
        print(f"[!] Failed to fetch Frida releases: {fridaInfo.get('message', 'Unknown error')}")
        sys.exit(1)

    print(f"[*] Current architecture: {runADBCommand('getprop ro.product.cpu.abi')}")
    print(f"[*] Latest frida version: {fridaInfo['name']}")

    fridaInstallLinks = []
    index = 1
    for asset in fridaInfo["assets"]:
        assetName = asset["name"]
        if not re.match(r"frida-server-.*-android", assetName):
            continue
        fridaInstallLinks.append((assetName, asset["browser_download_url"]))
        print(f"[-] {index}) {assetName}")
        index += 1

    if not fridaInstallLinks:
        print("[!] No frida-server builds found in the release!")
        sys.exit(1)

    choice = prompt_choice("[?] Which frida server version do you want to install: ", len(fridaInstallLinks))
    chosenOptionName, chosenOptionLink = fridaInstallLinks[choice - 1]

    print("[*] Downloading frida server")
    downloadFileFromUrl(chosenOptionLink, chosenOptionName, EXTERNAL_PATH)

    print("[*] Extracting server")
    extractXZ(
        os.path.join(EXTERNAL_PATH, chosenOptionName),
        os.path.join(EXTERNAL_PATH, "frida-server"),
    )

    print("[*] Pushing server to /data/local/tmp/ on AVD")
    frida_local = os.path.join(EXTERNAL_PATH, "frida-server")
    out = runOSCommand(["adb", "push", frida_local, "/data/local/tmp/"])
    print(out)

    print("[*] Changing permissions of server")
    runADBCommand("chmod 755 /data/local/tmp/frida-server", asRoot=True)

    print("[*] Running frida server")
    runADBCommand("nohup /data/local/tmp/frida-server > /dev/null 2>&1&", asRoot=True)

    print("[*] Checking if frida server is running")
    runningProcesses = runADBCommand("ps | grep frida-server")

    if "frida-server" in runningProcesses:
        print("[*] Frida server is running")
    else:
        print("[!] Failed to run frida server!")


def installProxyTool():
    proxyInfo = getLatestProxyToolRelease()
    if "assets" not in proxyInfo or not proxyInfo["assets"]:
        print(f"[!] Failed to fetch proxy tool release: {proxyInfo.get('message', 'Unknown error')}")
        sys.exit(1)

    downloadUrl = proxyInfo["assets"][0]["browser_download_url"]
    print(f"[*] Latest proxy tool version: {proxyInfo['name']}")

    print("[*] Downloading proxy tool")
    downloadFileFromUrl(downloadUrl, "proxy-tool.zip", EXTERNAL_PATH)

    print("[*] Extracting APK from zip")
    proxy_zip = os.path.join(EXTERNAL_PATH, "proxy-tool.zip")
    proxy_dir = os.path.join(EXTERNAL_PATH, "proxy-tool")
    extractZip(proxy_zip, proxy_dir)

    apkFiles = findFile("proxy-toggle.apk", EXTERNAL_PATH)
    if not apkFiles:
        print("[!] Could not find proxy-toggle.apk after extraction!")
        sys.exit(1)

    print("[*] Installing proxy tool")
    runOSCommand(["adb", "install", "-t", "-r", apkFiles[0]])

    print("[*] Setting tool permissions")
    runOSCommand(["adb", "shell", "pm", "grant",
                  "com.kinandcarta.create.proxytoggle",
                  "android.permission.WRITE_SECURE_SETTINGS"])

    if isProxyToolInstalled():
        print("[*] Successfully installed proxy tool")
    else:
        print("[!] Failed to install proxy tool!")
        sys.exit(1)


def installTrustUserCertsModule():
    if not isDeviceRooted():
        print("[!] AVD is not rooted!")
        sys.exit(1)

    if not isMagiskInstalled():
        print("[!] Magisk is not installed!")
        sys.exit(1)

    moduleInfo = getLatestMagiskTrustUserCertsRelease()
    if "assets" not in moduleInfo or not moduleInfo["assets"]:
        print(f"[!] Failed to fetch module release: {moduleInfo.get('message', 'Unknown error')}")
        sys.exit(1)

    downloadUrl = moduleInfo["assets"][0]["browser_download_url"]
    print(f"[*] Latest MagiskTrustUserCerts module version: {moduleInfo['name']}")

    print("[*] Downloading module")
    downloadFileFromUrl(downloadUrl, "MagiskTrustUserCerts.zip", EXTERNAL_PATH)

    print("[*] Pushing module to /data/local/tmp/ on AVD")
    module_local = os.path.join(EXTERNAL_PATH, "MagiskTrustUserCerts.zip")
    out = runOSCommand(["adb", "push", module_local, "/data/local/tmp/"])
    print(out)

    print("[*] Installing module with Magisk")
    out = runADBCommand("magisk --install-module /data/local/tmp/MagiskTrustUserCerts.zip", asRoot=True)
    print(out)

    print("[*] Rebooting AVD")
    runOSCommand(["adb", "reboot"])


def installBurpCert():
    print("[*] Make sure Burp Suite is running")
    proxy = input("[?] Where is Burp Suite listening (e.g. localhost:8080): ").strip()

    if not proxy:
        proxy = "localhost:8080"

    # Basic input validation
    if not re.match(r"^[\w.-]+:\d{1,5}$", proxy):
        print("[!] Invalid proxy format. Use host:port (e.g. localhost:8080)")
        sys.exit(1)

    print("[*] Downloading cert")
    downloadBurpCert(proxy, EXTERNAL_PATH)

    cert_path = os.path.join(EXTERNAL_PATH, "cert.cer")
    print("[*] Moving cert to download folder on AVD")
    out = runOSCommand(["adb", "push", cert_path, "/sdcard/Download"])
    print(out)


def fullSetup():
    """Run all steps in sequence for a complete AVD setup."""
    print("[*] Starting full AVD setup...\n")
    rootDevice()
    installFridaServer()
    installProxyTool()
    installTrustUserCertsModule()
    installBurpCert()
    print("\n[*] Full setup complete!")


MENU_OPTIONS = [
    ("Root AVD", rootDevice),
    ("Install Frida Server", installFridaServer),
    ("Install Proxy Tool", installProxyTool),
    ("Install MagiskTrustUserCerts Module", installTrustUserCertsModule),
    ("Install Burp Suite Certificate", installBurpCert),
    ("Full Setup (all of the above)", fullSetup),
]


def main():
    clearScreen()
    showHeader()
    preflight_check()

    for i, (label, _) in enumerate(MENU_OPTIONS):
        print(f"  {i + 1}) {label}")
    print(f"  0) Exit")
    print()

    try:
        choice = int(input("[?] Select an option: ").strip())
    except ValueError:
        print("[!] Invalid option!")
        sys.exit(1)

    if choice == 0:
        print("[*] Bye!")
        sys.exit(0)

    if choice < 1 or choice > len(MENU_OPTIONS):
        print("[!] Invalid option!")
        sys.exit(1)

    print()
    _, action = MENU_OPTIONS[choice - 1]
    action()


if __name__ == "__main__":
    main()
