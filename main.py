from src.utils import *
import os

externalPath = r".\external"


def main():

    showHeader()

    # Check if ADB is installed and accessible
    print("[*] Checking for ADB...")
    if not hasAdb():
        print("[!] ADB was not found! Make sure you have it installed and in your path.")
        exit()
    else:
        print(f"[*] ADB was found: {adbPath()}")

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
    out = runOSCommand(f"rootAVD.bat {extractedPath}").strip()
    print(out)
    os.chdir("../")

    input("[*] Restart your AVD and press ENTER to continue...")

    # Check if device is rooted
    if isDeviceRooted():
        print("[*] Device was rooted successfully.")
    else:
        print("[!] Failed to root device!")
        exit()


if __name__ == "__main__":
    main()
