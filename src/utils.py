import subprocess, os, re, requests, lzma

def runOSCommand(command):
    return subprocess.run(command, shell=True, capture_output=True, text=True).stdout.strip()


def runADBCommand(command, asRoot=False):
    if hasAdb() and isDeviceAttached():
        if asRoot:
            return runOSCommand(f"adb shell su -c \"{command}\"")
        else:
            return runOSCommand(f"adb shell {command}")

    else:
        print("[!] Unable to run adb command")
        exit()


def isDeviceRooted():
    return "root" in runADBCommand("whoami", asRoot=True)

def adbPath():
    return runOSCommand("where adb")


def hasAdb():
    return "Could not find" not in adbPath()


def isDeviceAttached():
    out = runOSCommand("adb devices")
    linesAmount = len(out.split("\n"))
    return linesAmount > 1


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
    print("""
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
