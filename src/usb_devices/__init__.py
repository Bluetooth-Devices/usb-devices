from __future__ import annotations

__version__ = "0.5.0"

import asyncio
import logging

try:
    from fcntl import ioctl
except ImportError:
    ioctl = None  # type: ignore

from pathlib import Path

_LOGGER = logging.getLogger(__name__)

BLUETOOTH_DEVICE_PATH = Path("/sys/class/bluetooth")
USB_DEVICE_PATH = Path("/sys/bus/usb/devices")
USB_DEVFS_PATH = Path("/dev/bus/usb")
# _IO('U', 20) constant in the linux kernel.
USBDEVFS_RESET = ord("U") << (4 * 2) | 20


class NotAUSBDeviceError(ValueError):
    """Raised when a device is not a USB device."""


__all__ = [
    "USBDevice",
    "BluetoothDevice",
    "NotAUSBDeviceError",
]


class BluetoothDevice:

    __slots__ = ("hci", "path", "device_path", "usb_device")

    def __init__(self, hci: int) -> None:
        """Initialize a BluetoothDevice object."""
        self.hci = hci
        self.path = BLUETOOTH_DEVICE_PATH / f"hci{self.hci}"
        self.device_path = self.path / "device"
        self.usb_device: USBDevice | None = None

    async def async_setup(self) -> None:
        """Set up a Bluetooth device."""
        await asyncio.get_running_loop().run_in_executor(None, self.setup)

    async def async_reset(self) -> bool:
        """Reset a Bluetooth device."""
        return await asyncio.get_running_loop().run_in_executor(None, self.reset)

    def reset(self) -> bool:
        """Reset a Bluetooth device.

        Returns ``True`` on success, ``False`` if the underlying USB reset
        could not be performed (device gone, permission denied, ioctl
        failure, missing sysfs metadata). Errors are logged at DEBUG;
        this method does not raise on transient I/O conditions so callers
        can use the return value to drive recovery logic.
        """
        if self.usb_device is None:
            try:
                self.setup()
            except OSError as err:
                _LOGGER.debug(
                    "BluetoothDevice(hci%s) setup failed during reset: %s",
                    self.hci,
                    err,
                )
                return False
        assert self.usb_device is not None  # nosec
        return self.usb_device.reset()

    def setup(self) -> None:
        """Create a USBDevice object."""
        path = self.device_path.readlink()
        self.usb_device = USBDevice(path.parts[-1])
        self.usb_device.setup()


class USBDevice:

    __slots__ = (
        "id_str",
        "bus_port_id",
        "bus_id",
        "port_id",
        "interface_id",
        "manufacturer",
        "product",
        "product_id",
        "vendor_id",
        "dev_num",
        "usb_devfs_path",
        "path",
    )
    _files = {
        "manufacturer": "manufacturer",
        "product": "product",
        "product_id": "idProduct",
        "vendor_id": "idVendor",
        "dev_num": "devnum",
    }

    def __init__(self, id_str: str) -> None:
        """Initialize a USBDevice object."""
        if ":" not in id_str or "-" not in id_str:
            raise NotAUSBDeviceError(f"{id_str} is not a USB device")
        self.id_str = id_str  # 1-1.2.2:1.0
        bus_port_id, interface_id = id_str.split(":")
        self.bus_port_id = bus_port_id
        bus_id, port_id = bus_port_id.split("-")
        self.bus_id = bus_id
        self.port_id = port_id
        self.interface_id = interface_id
        self.manufacturer: str | None = None
        self.product: str | None = None
        self.product_id: str | None = None
        self.vendor_id: str | None = None
        self.dev_num: str | None = None
        self.path = USB_DEVICE_PATH / bus_port_id
        self.usb_devfs_path: Path | None = None

    async def async_setup(self) -> None:
        """Set up a USB device."""
        await asyncio.get_running_loop().run_in_executor(None, self.setup)

    async def async_reset(self) -> bool:
        """Reset the USB device."""
        return await asyncio.get_running_loop().run_in_executor(None, self.reset)

    def setup(self) -> None:
        """Read the USB device."""
        for key, value in self._files.items():
            try:
                setattr(self, key, self.path.joinpath(value).read_text().strip())
            except FileNotFoundError:
                if key not in ("manufacturer", "product"):
                    raise
        self.product = self.product or self.product_id
        self.manufacturer = self.manufacturer or self.vendor_id
        assert self.dev_num is not None  # nosec
        self.usb_devfs_path = (
            USB_DEVFS_PATH
            / f"{int(self.bus_id):03}"  # noqa
            / f"{int(self.dev_num):03}"  # noqa
        )

    def reset(self) -> bool:
        """Reset the USB device.

        Returns ``True`` if the USBDEVFS_RESET ioctl succeeded, ``False``
        otherwise. Failure modes include: ``fcntl`` unavailable (non-Linux),
        device unplugged between setup and reset (FileNotFoundError),
        insufficient permissions on ``/dev/bus/usb`` (PermissionError),
        and ioctl errors from the kernel (e.g. ENODEV, EBUSY). All such
        errors are logged at DEBUG and converted to ``False`` so callers
        can rely on the bool contract.
        """
        if ioctl is None:
            return False  # type: ignore
        if self.usb_devfs_path is None:
            try:
                self.setup()
            except OSError as err:
                _LOGGER.debug(
                    "USBDevice(%s) setup failed during reset: %s",
                    self.id_str,
                    err,
                )
                return False
        assert self.usb_devfs_path is not None  # nosec
        try:
            with self.usb_devfs_path.open("w") as usb_dev:
                return ioctl(usb_dev, USBDEVFS_RESET, 0) > -1
        except OSError as err:
            _LOGGER.debug("USBDevice(%s) reset ioctl failed: %s", self.id_str, err)
            return False
