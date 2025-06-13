import os
import sys
import platform
import subprocess
import time

PYTHON_PACKAGES = [
    "PyQt5",
    "pyserial",
    "opencv-python",
    "Pillow",
    "numpy",
    "requests",
    "easyocr",
    "ultralytics",
    "imagehash",
    "tqdm",
    "scikit-image",
    "python-dateutil"
]

def install_packages():
    python_exe = "python" if platform.system() == "Windows" else "python3"
    print("Installing required Python packages...")
    for package in PYTHON_PACKAGES:
        print(f"Installing {package}...")
        try:
            subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", package], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {package}: {e}")
            print("You might want to specify compatible versions or troubleshoot the package conflicts.")
            return False
    return True

def main():
    if not install_packages():
        print("Failed to install some packages. Please check the errors above.")
        return
    print("\nInstallation completed successfully!")
    print("The window will close in 10 seconds.")
    time.sleep(10)
    sys.exit()

if __name__ == "__main__":
    main()