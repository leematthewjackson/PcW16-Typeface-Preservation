# Stage F: For Windows and macOS users, Linux in VirtualBox

The conversion tools are documented and tested on Linux only. If you don't have a Linux computer, run Linux in a **virtual machine**: a computer emulated inside a window on your own. It's free and leaves your system as it is.

This guide gives the outline. VirtualBox and the Linux distributions have their own detailed, up-to-date instructions, linked below.

## F1. Install VirtualBox

Download VirtualBox for your system from the official site, https://www.virtualbox.org/wiki/Downloads, and install it. On Macs with Apple silicon (M1 and later), check that site for current support; on those Macs you may need an ARM64 version of Linux.

## F2. Get a Linux distribution

Ubuntu Desktop is a good choice for beginners: download the installer image (an `.iso` file) from https://ubuntu.com/download/desktop. Debian (https://www.debian.org/distrib/) or Linux Mint (https://linuxmint.com/download.php) work just as well. Choose the 64-bit version that matches your computer.

## F3. Create the virtual machine

In VirtualBox choose **New**, then:

1. give it a name, for example `pcw16-linux`, and select the `.iso` file you downloaded;
2. give it at least **4 GB of memory** and **25 GB of disk**;
3. start it and follow the Linux installer. The installation happens inside the virtual machine only.

VirtualBox's manual covers this in detail: https://www.virtualbox.org/manual/.

## F4. Move the capture files into the virtual machine

The simplest ways:

* **Shared folder:** in VirtualBox, open the virtual machine's **Settings → Shared Folders**, add a folder on your computer and tick *Auto-mount*. Inside Linux it then appears under `/media/`. You may need to install the VirtualBox *Guest Additions* and add your user to the `vboxsf` group; the VirtualBox manual explains how.
* **Or** pack the capture files into a ZIP file, then download or copy it inside the virtual machine, for example from a USB stick or a cloud drive you open in the virtual machine's web browser.

Copy the files into a folder such as `~/pcw16-captures`, and download the toolkit inside the virtual machine (Stage A3).

## F5. Convert

Follow [Stage E](converting-on-linux.md) inside the virtual machine. To use the fonts on Windows or macOS afterwards, copy the `.ttf` files back out through the shared folder and install them as usual: on Windows, right-click → **Install**; on macOS, double-click → **Install Font**.
