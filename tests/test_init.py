from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import usb_devices
from usb_devices import BluetoothDevice, NotAUSBDeviceError, USBDevice

# BluetoothDevice exercises /sys/class/bluetooth symlinks — Linux-only.
requires_symlinks = pytest.mark.skipif(
    sys.platform == "win32",
    reason="symlink + sysfs layout is Linux-specific",
)


def test_bluetooth_device() -> None:
    assert BluetoothDevice(0)
    assert BluetoothDevice(1)


def test_usb_device() -> None:
    assert USBDevice("1-1.2.2:1.0")
    with pytest.raises(NotAUSBDeviceError):
        USBDevice("ttyAMA0")


def test_usb_device_parses_id_str() -> None:
    dev = USBDevice("1-1.2.2:1.0")
    assert dev.id_str == "1-1.2.2:1.0"
    assert dev.bus_port_id == "1-1.2.2"
    assert dev.bus_id == "1"
    assert dev.port_id == "1.2.2"
    assert dev.interface_id == "1.0"
    assert dev.manufacturer is None
    assert dev.product is None
    assert dev.usb_devfs_path is None


def test_usb_device_rejects_non_usb_id() -> None:
    with pytest.raises(NotAUSBDeviceError):
        USBDevice("ttyAMA0")
    with pytest.raises(NotAUSBDeviceError):
        USBDevice("1-1.2.2")  # no colon
    with pytest.raises(NotAUSBDeviceError):
        USBDevice("1:1.0")  # no dash


def _write_usb_sysfs(tmp_path: Path, bus_port_id: str, files: dict[str, str]) -> Path:
    dev_dir = tmp_path / bus_port_id
    dev_dir.mkdir(parents=True)
    for name, value in files.items():
        (dev_dir / name).write_text(value)
    return dev_dir


def test_usb_device_setup_reads_sysfs(tmp_path: Path) -> None:
    _write_usb_sysfs(
        tmp_path,
        "1-1.2.2",
        {
            "manufacturer": "Realtek\n",
            "product": "Bluetooth 5.1 Radio\n",
            "idProduct": "a725\n",
            "idVendor": "0bda\n",
            "devnum": "11\n",
        },
    )
    dev = USBDevice("1-1.2.2:1.0")
    dev.path = tmp_path / "1-1.2.2"
    dev.setup()
    assert dev.manufacturer == "Realtek"
    assert dev.product == "Bluetooth 5.1 Radio"
    assert dev.product_id == "a725"
    assert dev.vendor_id == "0bda"
    assert dev.dev_num == "11"
    assert dev.usb_devfs_path is not None
    assert dev.usb_devfs_path.parts[-2:] == ("001", "011")


def test_usb_device_setup_missing_manufacturer_falls_back(tmp_path: Path) -> None:
    _write_usb_sysfs(
        tmp_path,
        "1-1.2.2",
        {
            "idProduct": "a725",
            "idVendor": "0bda",
            "devnum": "11",
        },
    )
    dev = USBDevice("1-1.2.2:1.0")
    dev.path = tmp_path / "1-1.2.2"
    dev.setup()
    assert dev.manufacturer == "0bda"
    assert dev.product == "a725"


def test_usb_device_setup_non_ascii_sysfs(tmp_path: Path) -> None:
    """Manufacturer/product strings often contain non-ASCII bytes (USB string
    descriptors are UTF-16 LE in the device; the kernel exposes them as UTF-8
    in sysfs). read_text() must decode them as UTF-8 regardless of the
    process locale (LANG=C / LC_ALL=C is common in containers)."""
    dev_dir = tmp_path / "1-1.2.2"
    dev_dir.mkdir(parents=True)
    (dev_dir / "manufacturer").write_bytes("Mediatek µ\n".encode())
    (dev_dir / "product").write_bytes("Bluetooth™ Radio\n".encode())
    (dev_dir / "idProduct").write_text("a725\n")
    (dev_dir / "idVendor").write_text("0bda\n")
    (dev_dir / "devnum").write_text("11\n")
    dev = USBDevice("1-1.2.2:1.0")
    dev.path = dev_dir
    dev.setup()
    assert dev.manufacturer == "Mediatek µ"
    assert dev.product == "Bluetooth™ Radio"


def test_usb_device_setup_invalid_utf8_replaced(tmp_path: Path) -> None:
    """Invalid byte sequences in sysfs strings should not crash setup —
    errors='replace' substitutes the replacement character so callers see
    a degraded-but-usable string instead of an exception."""
    dev_dir = tmp_path / "1-1.2.2"
    dev_dir.mkdir(parents=True)
    (dev_dir / "manufacturer").write_bytes(b"bad\xffbyte\n")
    (dev_dir / "product").write_bytes(b"prod\xfe\n")
    (dev_dir / "idProduct").write_text("a725\n")
    (dev_dir / "idVendor").write_text("0bda\n")
    (dev_dir / "devnum").write_text("11\n")
    dev = USBDevice("1-1.2.2:1.0")
    dev.path = dev_dir
    dev.setup()
    assert "bad" in dev.manufacturer  # type: ignore[operator]
    assert "byte" in dev.manufacturer  # type: ignore[operator]
    assert "prod" in dev.product  # type: ignore[operator]


def test_usb_device_setup_missing_required_file_raises(tmp_path: Path) -> None:
    _write_usb_sysfs(
        tmp_path,
        "1-1.2.2",
        {"manufacturer": "Realtek", "product": "Bluetooth"},
    )
    dev = USBDevice("1-1.2.2:1.0")
    dev.path = tmp_path / "1-1.2.2"
    with pytest.raises(FileNotFoundError):
        dev.setup()


def test_usb_device_reset_returns_false_when_ioctl_unavailable(
    tmp_path: Path,
) -> None:
    dev = USBDevice("1-1.2.2:1.0")
    dev.usb_devfs_path = tmp_path / "usbdev"
    dev.usb_devfs_path.write_text("")
    with patch.object(usb_devices, "ioctl", None):
        assert dev.reset() is False


def test_usb_device_reset_calls_ioctl(tmp_path: Path) -> None:
    dev = USBDevice("1-1.2.2:1.0")
    dev.usb_devfs_path = tmp_path / "usbdev"
    dev.usb_devfs_path.write_text("")
    with patch.object(usb_devices, "ioctl", lambda *a, **k: 0):
        assert dev.reset() is True
    with patch.object(usb_devices, "ioctl", lambda *a, **k: -1):
        assert dev.reset() is False


def test_usb_device_reset_calls_setup_when_needed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(usb_devices, "USB_DEVFS_PATH", tmp_path / "devfs")
    _write_usb_sysfs(
        tmp_path,
        "1-1.2.2",
        {"idProduct": "a", "idVendor": "b", "devnum": "11"},
    )
    devfs_dir = tmp_path / "devfs" / "001"
    devfs_dir.mkdir(parents=True)
    (devfs_dir / "011").write_text("")
    dev = USBDevice("1-1.2.2:1.0")
    dev.path = tmp_path / "1-1.2.2"
    with patch.object(usb_devices, "ioctl", lambda *a, **k: 0):
        assert dev.reset() is True
    assert dev.usb_devfs_path is not None


def test_usb_device_async_setup(tmp_path: Path) -> None:
    _write_usb_sysfs(
        tmp_path,
        "1-1.2.2",
        {"idProduct": "a725", "idVendor": "0bda", "devnum": "11"},
    )
    dev = USBDevice("1-1.2.2:1.0")
    dev.path = tmp_path / "1-1.2.2"
    asyncio.run(dev.async_setup())
    assert dev.product_id == "a725"


def test_usb_device_async_reset(tmp_path: Path) -> None:
    dev = USBDevice("1-1.2.2:1.0")
    dev.usb_devfs_path = tmp_path / "usbdev"
    dev.usb_devfs_path.write_text("")
    with patch.object(usb_devices, "ioctl", lambda *a, **k: 0):
        assert asyncio.run(dev.async_reset()) is True


def test_bluetooth_device_init_paths() -> None:
    dev = BluetoothDevice(3)
    assert dev.hci == 3
    assert dev.path.name == "hci3"
    assert dev.device_path.name == "device"
    assert dev.usb_device is None


def _build_bt_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    bt_path = tmp_path / "bluetooth"
    usb_path = tmp_path / "usb"
    (bt_path / "hci0").mkdir(parents=True)
    (usb_path / "1-1.2.2:1.0").mkdir(parents=True)
    _write_usb_sysfs(
        usb_path,
        "1-1.2.2",
        {"idProduct": "a725", "idVendor": "0bda", "devnum": "11"},
    )
    (bt_path / "hci0" / "device").symlink_to(usb_path / "1-1.2.2:1.0")
    monkeypatch.setattr(usb_devices, "USB_DEVICE_PATH", usb_path)
    return bt_path, usb_path


@requires_symlinks
def test_bluetooth_device_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bt_path, _ = _build_bt_tree(tmp_path, monkeypatch)
    dev = BluetoothDevice(0)
    dev.path = bt_path / "hci0"
    dev.device_path = dev.path / "device"
    dev.setup()
    assert dev.usb_device is not None
    assert dev.usb_device.id_str == "1-1.2.2:1.0"


@requires_symlinks
def test_bluetooth_device_reset_calls_setup_when_needed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bt_path, _ = _build_bt_tree(tmp_path, monkeypatch)
    devfs = tmp_path / "devfs" / "001"
    devfs.mkdir(parents=True)
    (devfs / "011").write_text("")
    monkeypatch.setattr(usb_devices, "USB_DEVFS_PATH", tmp_path / "devfs")
    dev = BluetoothDevice(0)
    dev.path = bt_path / "hci0"
    dev.device_path = dev.path / "device"
    with patch.object(usb_devices, "ioctl", lambda *a, **k: 0):
        assert dev.reset() is True
    assert dev.usb_device is not None


@requires_symlinks
def test_bluetooth_device_async_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bt_path, _ = _build_bt_tree(tmp_path, monkeypatch)
    dev = BluetoothDevice(0)
    dev.path = bt_path / "hci0"
    dev.device_path = dev.path / "device"
    asyncio.run(dev.async_setup())
    assert dev.usb_device is not None


@requires_symlinks
def test_bluetooth_device_async_reset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bt_path, _ = _build_bt_tree(tmp_path, monkeypatch)
    devfs = tmp_path / "devfs" / "001"
    devfs.mkdir(parents=True)
    (devfs / "011").write_text("")
    monkeypatch.setattr(usb_devices, "USB_DEVFS_PATH", tmp_path / "devfs")
    dev = BluetoothDevice(0)
    dev.path = bt_path / "hci0"
    dev.device_path = dev.path / "device"
    with patch.object(usb_devices, "ioctl", lambda *a, **k: 0):
        assert asyncio.run(dev.async_reset()) is True
