#!/bin/sh
echo 80000000.i2c > /sys/bus/platform/drivers/xiic-i2c/unbind
echo uio_pdrv_genirq > /sys/devices/platform/amba/80000000.i2c/driver_override
echo 80000000.i2c > /sys/bus/platform/drivers/uio_pdrv_genirq/bind
chmod a+rw /dev/uio*
