import asyncio
import logging

from usb_devices import BluetoothDevice, NotAUSBDeviceError

logging.basicConfig(level=logging.INFO)
logging.getLogger("usb_devices").setLevel(logging.DEBUG)


async def run(device: int) -> None:
    dev = BluetoothDevice(device)
    try:
        reset_ok = await dev.async_reset()
    except NotAUSBDeviceError:
        print(f"hci{device} is not a USB device")
    except FileNotFoundError:
        print(f"hci{device} not found")
    else:
        if reset_ok:
            print(f"Reset of hci{device} succeeded")
        else:
            print(f"Reset of hci{device} failed")


asyncio.run(run(0))
