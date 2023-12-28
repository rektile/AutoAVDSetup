import subprocess, os, re, requests, lzma
from zipfile import ZipFile

def runOSCommand(command):
    return subprocess.run(command, shell=True, capture_output=True, text=True).stdout.strip()


def runADBCommand(command, asRoot=False):
    if hasAdb() and len(listAttachedDevices()) == 1:
        if asRoot:
            return runOSCommand(f"adb shell su -c \"{command}\"")
        else:
            return runOSCommand(f"adb shell \"{command}\"")

    else:
        print("[!] Unable to run adb command")
        exit()


def isDeviceRooted():
    return "root" in runADBCommand("whoami", asRoot=True)

def adbPath():
    return runOSCommand("where adb")


def hasAdb():
    return "Could not find" not in adbPath()


def listAttachedDevices():
    return runOSCommand("adb devices").split("\n")[1:]


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
    return requests.get("https://api.github.com/repos/frida/frida/releases/latest").json()


def downloadFileFromUrl(url, fileName, path):
    r = requests.get(url)
    with open(f"{path}\\{fileName}", "wb") as f:
        f.write(r.content)


def extractXZ(fileIn, fileOut):
    with lzma.open(fileIn) as f, open(fileOut, "wb") as f2:
        f2.write(f.read())


def doesAndroidVersionMatch(path):
    return f"android-{runADBCommand('getprop ro.build.version.sdk')}" in path


def isMagiskInstalled():
    return "com.topjohnwu.magisk" in runADBCommand("cmd package list packages | grep com.topjohnwu.magisk")


def getLatestProxyToolRelease():
    return requests.get("https://api.github.com/repos/theappbusiness/android-proxy-toggle/releases/latest").json()


def extractZip(file, outputDir):
    with ZipFile(file, "r") as z:
        z.extractall(outputDir)


def isProxyToolInstalled():
    return "com.kinandcarta.create.proxytoggle" in runADBCommand("cmd package list packages | grep com.kinandcarta.create.proxytoggle")