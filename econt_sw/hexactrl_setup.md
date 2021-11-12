# Hexa-controller setup

1. Connect Zynq and place heat sink
2. Load SD card:
   * If you do not have another working SD card available:
     * To get `boot` file from scratch, go to [Trenz TE0820 website](https://shop.trenz-electronic.de/en/TE0820-04-2BE21FL-MPSoC-Module-with-Xilinx-Zynq-UltraScale-ZU2EG-1E-2-GByte-DDR4-4-x-5-cm-LP?path=Trenz_Electronic/Modules_and_Module_Carriers/4x5/TE0820/Reference_Design/2019.2/test_board) and look into `Reference Design - Source Code and Configuration Files` - download 1 File.
     * Unzip the file `TE0820-test_board-vivado_2020.2-build_5_20210601084124` and look into `prebuilt/boot_images`. 
     * The `BOOT.bin` comes from the folder `4cg_1e_2gb` (or for older versions `prebuilt/boot_images/3eg_2gb/`) but `image.ub` comes from the petalinux directory.
     * You can mount it using:
     ```
     mount boot
     mount root
     ```
   * A better option is to start from a working SD card. Follow instructions from [here](https://beebom.com/how-clone-raspberry-pi-sd-card-windows-linux-macos/) or [here](https://www.cyberciti.biz/faq/how-to-create-disk-image-on-mac-os-x-with-dd-command/)
     * Insert the SD card in your PC using a USB or built-in card reader. 
     * For MacOS enter a terminal: `diskutil list`, for linux `sudo fdisk -l`. This will list all filesystems.
     * Find the device name of your SD card, e.g. 
     ```
     /dev/disk2 (external, physical):
     #:                       TYPE NAME                    SIZE       IDENTIFIER
     0:     FDisk_partition_scheme                        *32.2 GB    disk2
     1:                 DOS_FAT_32 BOOT                    1.1 GB     disk2s1
     2:                      Linux                         31.1 GB    disk2s2
     ```
     * Use the `dd` command to write the image to your hard disk.
     ```
     sudo dd if=/dev/disk2 of=sd_card_copy.img bs=1m
     ```
     Here, the if parameter (input file) specifies the file to clone. In my case, it is `/dev/disk2`, which is my SD card’s device name. 
     Replace it with the device name of yours. The of parameter (output file) specifies the file name to write to. I chose `sd_card_copy.img` in my home directory.
     You can also use `bs` that sets both input and output block size to n bytes
     
     You will not see any output from the command until after the cloning is complete, and that might take a while, depending on the size of your SD card. Once it is complete, you will see an output like the following:
     ```
     30727+1 records in
     30727+1 records out
     32220119040 bytes transferred in 5043.025013 secs (6389046 bytes/sec)
     ```
    
     You can now remove the SD card. Enter the new one and do:
     ```
     sudo dd if=sd_card_copy.img of=/dev/disk2
     ```
3. Replace SD card on the board.
4. Connect to ethernet and power the board.
   * If SD card has the correct boot files, the green light should be there, and the red light next to it should go off.
   * First, you need to find the IP address. 
     Try pinging until connected:
     ```
     for i in `seq 90 199`; do ping -w 1 192.168.1.$i; done
     ```
     until, e.g.
     ```
     PING 192.168.1.91 (192.168.1.91) 56(84) bytes of data.
     64 bytes from 192.168.1.91: icmp_seq=1 ttl=64 time=0.111 ms

     --- 192.168.1.91 ping statistics ---
     1 packets transmitted, 1 received, 0% packet loss, time 0ms
     rtt min/avg/max/mdev = 0.111/0.111/0.111/0.000 ms
     PING 192.168.1.92 (192.168.1.92) 56(84) bytes of data.
     ```
     Now, log in and get the mac address, e.g.:
     ```
     ssh HGCAL_dev@192.168.1.91
     ip addr show
     ```
     and it will show, e.g.
     ```
     # for econ-tester 1 (192.168.1.45)
     link/ether 04:91:62:bf:cb:cb brd ff:ff:ff:ff:ff:ff
     # for econ-tester 2 (192.168.1.46)
     link/ether 04:91:62:bf:b9:ef
     # for econ-tester 3 (hexacontroller from UMN) (192.168.1.48):
     link/ether 04:91:62:bf:c0:d2 brd ff:ff:ff:ff:ff:ff
     # for econ-tester 4 (hexacontroller from Aidan) (to be set up as 192.168.1.49):
     
     ```
     
     Now, log in to hcalpro (password 2013%hcalpro):
     ```
     # log in as sudo (password: WeLuVL8z8)
     su
     # then edit to add a fixed address
     /etc/dhcp/dhcpd.conf
     # e.g.
     host econ-tester3{
         hardware ethernet 04:91:62:bf:c0:d2;
         fixed-address 192.168.1.48;
     }
     # then, restart dhcp server
     service dhcpd restart
     # then, reboot
     sudo reboot
     ```     
     Then connect:
     ```
     ssh HGCAL_dev@192.168.1.XX
     ```
     
4. Copy version of the firmware into the board:
    ```
    # e.g. scp into hcalpro 
    scp -o GSSAPIAuthentication=yes -r FIRMWARE_VERSION.tar.gz  hcalpro@cmsnghcal01.fnal.gov:/home/hcalpro/cmantill/firmware/
    # go into hcalpro
    cd /home/hcalpro/cmantill/firmware/
    # copy to board
    scp -r FIRMWARE_VERSION.tar.gz  HGCAL_dev@192.168.1.45:~HGCAL_dev/firmware/
    ```
5. Unpack it in ~HGCAL_dev/firmware/ and rename it if necessary (e.g. to include the date on which it was built)
6. Install `mylittledt`
    ```
    cd mylittledt/
    git remote add hgcal-daq-sw ssh://git@gitlab.cern.ch:7999/hgcal-daq-sw/mylittledt.git
    git fetch hgcal-daq-sw
    git checkout -b tileboard hgcal-daq-sw/tileboard
    chmod +x load.sh
    ```
7. Load firmware:
    ```
    [HGCAL_dev@localhost mylittledt]$ sudo ./load.sh ~/firmware/econ-t-emu-solo-ROCv3-Sep9 && sudo chmod a+rw /dev/i2c-* /dev/uio*
    ```
