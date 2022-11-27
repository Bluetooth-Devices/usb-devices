import pytest

from usb_devices import BluetoothDevice, NotAUSBDeviceError, USBDevice


def test_bluetooth_device():
    assert BluetoothDevice(0)
    assert BluetoothDevice(1)


def test_usb_device():
    assert USBDevice("1-1.2.2:1.0")
    with pytest.raises(NotAUSBDeviceError):
        USBDevice("ttyAMA0")
