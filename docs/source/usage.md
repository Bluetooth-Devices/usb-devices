# Usage

`usb_devices` is a Linux-only helper for resolving Bluetooth HCI adapters back
to the USB device that exposes them, and for issuing a USB-level reset against
that device. It reads sysfs (`/sys/class/bluetooth`, `/sys/bus/usb/devices`)
and talks to usbdevfs (`/dev/bus/usb`) via the `USBDEVFS_RESET` ioctl.

## API overview

The package exposes two classes and one exception:

- `BluetoothDevice(hci: int)` — wraps an HCI index (e.g. `0` for `hci0`) and
  resolves it to the backing USB device through `/sys/class/bluetooth/hciN/device`.
- `USBDevice(id_str: str)` — wraps a USB interface id like `"1-1.2.2:1.0"` and
  reads its sysfs descriptors (`manufacturer`, `product`, `idVendor`,
  `idProduct`, `devnum`).
- `NotAUSBDeviceError` — raised by `USBDevice.__init__` when the id string
  does not look like a USB interface id.

Both classes provide synchronous methods (`setup`, `reset`) and async wrappers
(`async_setup`, `async_reset`) that off-load the blocking sysfs/ioctl work to
the default executor.

## Reading device info

```python
import asyncio

from usb_devices import BluetoothDevice, NotAUSBDeviceError


async def main() -> None:
    dev = BluetoothDevice(0)
    try:
        await dev.async_setup()
    except NotAUSBDeviceError:
        print("hci0 is not backed by a USB device")
        return
    except FileNotFoundError:
        print("hci0 not present")
        return

    usb = dev.usb_device
    assert usb is not None
    print(f"{usb.manufacturer} {usb.product} "
          f"({usb.vendor_id}:{usb.product_id}) on bus {usb.bus_id}")


asyncio.run(main())
```

`setup()` populates `manufacturer`, `product`, `vendor_id`, `product_id`,
`dev_num`, and the derived `usb_devfs_path`. When the `manufacturer` or
`product` sysfs entries are missing, they fall back to `vendor_id` /
`product_id`. Sysfs strings are decoded as UTF-8 with replacement, so
non-ASCII descriptors work under `LANG=C` containers as well.

## Resetting a device

```python
import asyncio

from usb_devices import BluetoothDevice, NotAUSBDeviceError


async def main() -> None:
    dev = BluetoothDevice(0)
    try:
        ok = await dev.async_reset()
    except NotAUSBDeviceError:
        print("hci0 is not backed by a USB device")
    except FileNotFoundError:
        print("hci0 not present")
    else:
        print("reset succeeded" if ok else "reset failed")


asyncio.run(main())
```

`reset()` returns `True` when the `USBDEVFS_RESET` ioctl succeeds and `False`
when it fails or when `fcntl.ioctl` is unavailable (e.g. on non-Linux
platforms). `reset()` calls `setup()` lazily the first time, so you can skip
an explicit setup call when you only need to reset.

Reset typically requires either root privileges or a udev rule granting
write access to `/dev/bus/usb/<bus>/<devnum>`.

## Platform notes

`usb_devices` is Linux-specific: it depends on the sysfs layout
(`/sys/class/bluetooth`, `/sys/bus/usb/devices`) and usbdevfs
(`/dev/bus/usb`). On non-Linux platforms, `fcntl.ioctl` is unavailable and
`reset()` returns `False`.
