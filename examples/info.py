import asyncio
import logging

from usb_devices import BluetoothDevice, NotAUSBDeviceError

logging.basicConfig(level=logging.INFO)
logging.getLogger("usb_devices").setLevel(logging.DEBUG)


async def run() -> None:
    loop = asyncio.get_running_loop()
    for i in range(0, 9):
        dev = BluetoothDevice(i)
        try:
            await loop.run_in_executor(None, dev.setup)
        except NotAUSBDeviceError:
            print(f"hci{i} is not a USB device")
            continue
        except FileNotFoundError:
            print(f"hci{i} not found")
            continue
        assert dev.usb_device is not None  # nosec
        print(
            f"hci{i} manufacturer: {dev.usb_device.manufacturer}, "
            f"product: {dev.usb_device.product}, "
            f"vendor_id: {dev.usb_device.vendor_id}, "
            f"product_id: {dev.usb_device.product_id}, "
            f"bus_id: {dev.usb_device.bus_id}, "
            f"dev_num: {dev.usb_device.dev_num}"
        )


asyncio.run(run())
