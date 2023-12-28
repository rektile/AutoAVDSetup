from src.utils import *
import os

externalPath = r".\external"


def rootDevice():

    print("[*] Listing installed AVD.")

    # Get all AVD ramdisk.img locations
    paths = getAVDLocations()
    if not paths:
        print("[!] No AVD found!")
        exit()

    # Show ramdisk.img files to user
    for i, path in enumerate(paths):
        print(f"[-] {i + 1}) {path}")

    try:
        print("[*] Make sure the AVD you want to root is running.")
        whichToRoot = int(input("[?] Which AVD do you want to root: ").strip())
    except ValueError:
        print("[!] That is not a valid option!")
        exit()

    # Check if chosen option is available
    if whichToRoot > len(paths) or whichToRoot < 1:
        print("[!] That is not a valid option!")
        exit()

    chosenOption = paths[whichToRoot - 1]
    extractedPath = extractPathForRootAVD(chosenOption)

    # Rooting chosen device
    print("[*] Rooting device...")
    os.chdir(externalPath)
    out = runOSCommand(f"rootAVD.bat {extractedPath}")
    print(out)
    os.chdir("../")

    input("[*] Restart your AVD and press ENTER to check if AVD is rooted...")
    print("[*] Make sure to accept root permissions on AVD")
    # Check if device is rooted
    if isDeviceRooted():
        print("[*] Device was rooted successfully.")
    else:
        print("[!] Failed to root device!")
        exit()


def installFridaServer():

    fridaInfo = getLatestFridaServerReleases()

    if not isDeviceRooted():
        print("[!] AVD is not rooted!")
        exit()

    print(f"[*] Latest frida version is: {fridaInfo['name']}")

    fridaInstallLinks = []

    # List all frida server versions
    index = 1
    for asset in fridaInfo["assets"]:

        assetName = asset['name']

        if not re.match(r"frida-server-.*-android", assetName):
            continue

        fridaInstallLinks.append((assetName, asset["browser_download_url"]))
        print(f"[-] {index}) {assetName}")
        index += 1

    try:
        whichFridaServerVersion = int(input("[?] Which frida server version do you want to install: "))
    except ValueError:
        print("[!] That is not a valid option!")
        exit()

    # Check if chosen option is available
    if whichFridaServerVersion > len(fridaInstallLinks) or whichFridaServerVersion < 1:
        print("[!] That is not a valid option!")
        exit()

    chosenOptionName, chosenOptionLink = fridaInstallLinks[whichFridaServerVersion - 1]

    print("[*] Downloading frida server")
    downloadFileFromUrl(chosenOptionLink, chosenOptionName, externalPath)

    print("[*] Extracting server")
    extractXZ(f"{externalPath}\\{chosenOptionName}", f"{externalPath}\\frida-server")

    # Push server to AVD
    print("[*] Pushing server to AVD")
    out = runOSCommand(f"adb push {externalPath}/frida-server /data/local/tmp/")
    print(out)

    # Change permissions of frida server
    print("[*] Changing permissions of server")
    runADBCommand("chmod 755 /data/local/tmp/frida-server", asRoot=True)

    # Run frida server
    print("[*] Running frida server")
    runADBCommand("nohup /data/local/tmp/frida-server > /dev/null 2>&1&", asRoot=True)

    print("[*] Checking if frida server is running")
    runningProcesses = runADBCommand("ps")

    if "frida-server" in runningProcesses:
        print("[*] Frida server is running")
    else:
        print("[!] Failed to run frida server!")


def main():

    showHeader()

    # Check if ADB is installed and accessible
    print("[*] Checking for ADB...")
    if not hasAdb():
        print("[!] ADB was not found! Make sure you have it installed and in your path.")
        exit()
    else:
        print(f"[*] ADB was found: {adbPath()}")

    # Check AVD is running
    print("[*] Checking if AVD is active...")
    if not isDeviceAttached():
        print("[!] No AVD is active!")
        exit()
    else:
        print("[*] Active AVD found")

    # List options of this tool
    print("[*] Listing program options")
    print("[-] 1) Root your AVD")
    print("[-] 2) Install frida server on your AVD")

    try:
        option = int(input("[?] What do you want to do: ").strip())

        if option == 1:
            rootDevice()
        elif option == 2:
            installFridaServer()
        else:
            print("[!] That is not a valid option!")
            exit()

    except ValueError:
        print("[!] That is not a valid option!")
        exit()


if __name__ == "__main__":
    main()
