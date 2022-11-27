import asyncio
import logging

from usb_devices import BluetoothDevice

logging.basicConfig(level=logging.INFO)
logging.getLogger("usb_devices").setLevel(logging.DEBUG)


async def run() -> None:
    dev = BluetoothDevice(0)
    if await dev.async_reset():
        print("Reset of hci0 succeeded")
    else:
        print("Reset of hci0 failed")


asyncio.run(run())
