import subprocess, os, re, sys, requests, lzma
from zipfile import ZipFile


def runOSCommand(command):
    """Run a command. Accepts a list (safe) or string (shell=True, use with caution)."""
    use_shell = isinstance(command, str)
    result = subprocess.run(command, shell=use_shell, capture_output=True, text=True)
    if result.returncode != 0 and result.stderr:
        print(f"[!] Command error: {result.stderr.strip()}")
    return result.stdout.strip()


def runInteractiveCommand(command):
    """Run a command interactively — stdin/stdout/stderr go directly to the terminal."""
    use_shell = isinstance(command, str)
    result = subprocess.run(command, shell=use_shell)
    return result.returncode


def runADBCommand(command, asRoot=False):
    if not hasAdb():
        print("[!] ADB not found in PATH!")
        sys.exit(1)

    devices = listAttachedDevices()
    if len(devices) == 0:
        print("[!] No device attached!")
        sys.exit(1)
    if len(devices) > 1:
        print("[!] Multiple devices attached. Please use only one device at a time.")
        sys.exit(1)

    if asRoot:
        return runOSCommand(["adb", "shell", "su", "-c", command])
    else:
        return runOSCommand(["adb", "shell", command])


def isDeviceRooted():
    return "root" in runADBCommand("whoami", asRoot=True)

def adbPath():
    return runOSCommand(["where", "adb"])


def hasAdb():
    return "Could not find" not in adbPath()


def listAttachedDevices():
    output = runOSCommand(["adb", "devices"])
    lines = output.strip().split("\n")[1:]  # skip header
    devices = [line.strip() for line in lines if line.strip() and "device" in line]
    return devices


def isDeviceAttached():
    return len(listAttachedDevices()) > 0


def getAVDLocations():
    fullPath = os.path.expandvars(r"%localappdata%\Android\Sdk\system-images")
    return findFile("ramdisk.img", f"{fullPath}")


def findFile(name, startPath):
    result = []

    for root, dir, files in os.walk(startPath):
        if name in files:
            result.append(os.path.join(root, name))
    return result


def extractPathForRootAVD(path):
    return re.findall(r"system-images\\.*", path)[0]

def clearScreen():
    os.system("cls")


def showHeader():
    print(r"""
   _____          __            _________   ____________    _________       __                
  /  _  \  __ ___/  |_  ____   /  _  \   \ /   /\______ \  /   _____/ _____/  |_ __ ________  
 /  /_\  \|  |  \   __\/  _ \ /  /_\  \   Y   /  |    |  \ \_____  \_/ __ \   __\  |  \____ \ 
/    |    \  |  /|  | (  <_> )    |    \     /   |    `   \/        \  ___/|  | |  |  /  |_> >
\____|__  /____/ |__|  \____/\____|__  /\___/   /_______  /_______  /\___  >__| |____/|   __/ 
        \/                           \/                 \/        \/     \/           |__|
-----------------------------------------------------------------------------------------------
""")


def getLatestFridaServerReleases():
    resp = requests.get("https://api.github.com/repos/frida/frida/releases/latest", timeout=10)
    resp.raise_for_status()
    return resp.json()

def getLatestMagiskTrustUserCertsRelease():
    resp = requests.get("https://api.github.com/repos/NVISOsecurity/MagiskTrustUserCerts/releases/latest", timeout=10)
    resp.raise_for_status()
    return resp.json()

def downloadFileFromUrl(url, fileName, path):
    r = requests.get(url, timeout=30, stream=True)
    r.raise_for_status()
    filepath = os.path.join(path, fileName)
    with open(filepath, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)


def extractXZ(fileIn, fileOut):
    with lzma.open(fileIn) as f, open(fileOut, "wb") as f2:
        f2.write(f.read())


def doesAndroidVersionMatch(path):
    return f"android-{runADBCommand('getprop ro.build.version.sdk')}" in path


def getRunningAVDImagePath():
    """Get the system-image path of the currently running AVD from its config."""
    try:
        avd_name = runOSCommand(["adb", "emu", "avd", "name"]).splitlines()[0].strip()
        if not avd_name:
            return None
        avd_dir = os.path.expandvars(rf"%USERPROFILE%\.android\avd\{avd_name}.avd")
        config_path = os.path.join(avd_dir, "config.ini")
        if not os.path.exists(config_path):
            return None
        with open(config_path, "r") as f:
            for line in f:
                if line.startswith("image.sysdir.1"):
                    # value is like: system-images\android-33\google_apis_playstore\x86_64\
                    sysdir = line.split("=", 1)[1].strip().rstrip("/\\")
                    return sysdir
    except Exception:
        pass
    return None


def isActiveAVDPath(path):
    """Check if a ramdisk.img path belongs to the currently running AVD."""
    active_sysdir = getRunningAVDImagePath()
    if not active_sysdir:
        return False
    # Normalize separators for comparison
    normalized_path = path.replace("/", "\\")
    normalized_sysdir = active_sysdir.replace("/", "\\")
    return normalized_sysdir in normalized_path


def getRunningAPILevel():
    """Get the API level of the running AVD."""
    try:
        return int(runADBCommand("getprop ro.build.version.sdk"))
    except (ValueError, TypeError):
        return 0


BUSYBOX_URLS = {
    "x86_64": "https://busybox.net/downloads/binaries/1.35.0-x86_64-linux-musl/busybox",
    "x86": "https://busybox.net/downloads/binaries/1.35.0-i686-linux-musl/busybox",
    "arm64-v8a": "https://busybox.net/downloads/binaries/1.35.0-aarch64-linux-musl/busybox",
    "armeabi-v7a": "https://busybox.net/downloads/binaries/1.35.0-armv7l-linux-musleabihf/busybox",
}

BUSYBOX_DEVICE_PATH = "/data/local/tmp/busybox_dl"


def pushBusyboxToDevice(externalPath):
    """Download a static busybox binary and push it to /data/local/tmp/ on the device."""
    abi = runADBCommand("getprop ro.product.cpu.abi")
    url = BUSYBOX_URLS.get(abi)
    if not url:
        print(f"[!] No busybox binary available for ABI: {abi}")
        return False

    local_path = os.path.join(externalPath, "busybox_dl")
    print(f"[*] Downloading static busybox for {abi}...")
    try:
        downloadFileFromUrl(url, "busybox_dl", externalPath)
    except Exception as e:
        print(f"[!] Failed to download busybox: {e}")
        return False

    print("[*] Pushing busybox to device...")
    out = runOSCommand(["adb", "push", local_path, BUSYBOX_DEVICE_PATH])
    if out:
        print(f"[-] {out}")
    runADBCommand(f"chmod 755 {BUSYBOX_DEVICE_PATH}")
    return True


def isMagiskInstalled():
    return "com.topjohnwu.magisk" in runADBCommand("cmd package list packages | grep com.topjohnwu.magisk")


def getLatestMagiskRelease():
    """Get the latest stable Magisk release info from GitHub."""
    resp = requests.get("https://api.github.com/repos/topjohnwu/Magisk/releases/latest", timeout=10)
    resp.raise_for_status()
    return resp.json()


def updateMagiskZip(externalPath):
    """Download the latest Magisk APK and save it as Magisk.zip for rootAVD."""
    try:
        release = getLatestMagiskRelease()
    except Exception as e:
        print(f"[!] Failed to fetch latest Magisk release: {e}")
        return False

    version = release.get("tag_name", "unknown")
    apk_url = None
    for asset in release.get("assets", []):
        if asset["name"].endswith(".apk"):
            apk_url = asset["browser_download_url"]
            break

    if not apk_url:
        print("[!] Could not find Magisk APK in release assets")
        return False

    magisk_path = os.path.join(externalPath, "Magisk.zip")
    backup_path = os.path.join(externalPath, "Magisk.zip.bak")

    # Backup the old one
    if os.path.exists(magisk_path):
        import shutil
        shutil.copy2(magisk_path, backup_path)
        print(f"[-] Backed up old Magisk.zip to Magisk.zip.bak")

    print(f"[*] Downloading Magisk {version}...")
    try:
        downloadFileFromUrl(apk_url, "Magisk.zip", externalPath)
    except Exception as e:
        print(f"[!] Failed to download Magisk: {e}")
        # Restore backup
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, magisk_path)
        return False

    print(f"[*] Magisk {version} ready")
    return True


def is16KBPageSize():
    """Check if the running AVD uses 16KB page size."""
    pagesize = runADBCommand("getconf PAGE_SIZE")
    try:
        return int(pagesize) > 4096
    except (ValueError, TypeError):
        return False


def getLatestProxyToolRelease():
    resp = requests.get("https://api.github.com/repos/theappbusiness/android-proxy-toggle/releases/latest", timeout=10)
    resp.raise_for_status()
    return resp.json()


def extractZip(file, outputDir):
    with ZipFile(file, "r") as z:
        z.extractall(outputDir)


def isProxyToolInstalled():
    return "com.kinandcarta.create.proxytoggle" in runADBCommand("cmd package list packages | grep com.kinandcarta.create.proxytoggle")


def downloadBurpCert(burpProxy, path):
    proxy = {"https": f"https://{burpProxy}", "http": f"http://{burpProxy}"}
    try:
        r = requests.get("http://burp/cert", proxies=proxy, verify=False, timeout=3)
        with open(f"{path}\\cert.cer", "wb") as f:
            f.write(r.content)
    except requests.exceptions.ConnectionError as E:
        print("[!] Unable to download cert, make sure you have entered the right proxy!")
        exit()