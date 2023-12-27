import subprocess, os


def runOSCommand(command):
    return subprocess.run(command.split(), shell=True, capture_output=True, text=True).stdout


def hasAdb():
    return "Could not find" not in runOSCommand("where adb")


def isDeviceAttached():
    out = runOSCommand("adb devices").strip()
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

