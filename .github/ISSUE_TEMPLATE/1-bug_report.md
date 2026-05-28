---
name: Bug report
about: Create a report to help us improve
labels: bug
---

**Describe the bug**
A clear and concise description of what's going wrong.

**To Reproduce**
Minimal code (or the exact `examples/info.py` / `examples/reset.py` invocation) that
triggers the bug. Include the full traceback if an exception is raised.

```python
# your snippet here
```

**Environment**

- `usb-devices` version: <!-- python -c "import usb_devices; print(usb_devices.__version__)" -->
- Python version: <!-- python --version -->
- OS / distribution: <!-- e.g. Ubuntu 24.04, Home Assistant OS 13.2, Debian Bookworm -->
- Kernel: <!-- uname -a -->
- Container runtime (if any): <!-- docker / podman / HA Supervisor / none -->

**Device context**

- `lsusb` output for the affected device:
  ```
  <!-- paste here -->
  ```
- For Bluetooth adapter bugs, the symlink target of `/sys/class/bluetooth/hciN/device`:
  ```
  <!-- readlink -f /sys/class/bluetooth/hci0/device -->
  ```
- Permissions on `/dev/bus/usb/BBB/DDD` for the device (only needed for reset bugs):
  ```
  <!-- ls -l /dev/bus/usb/001/011 -->
  ```

**Debug log**

Enable DEBUG logging for the library and paste the relevant lines:

```python
logging.getLogger("usb_devices").setLevel(logging.DEBUG)
```

```
<!-- paste log lines here -->
```

**Additional context**
Anything else worth mentioning (intermittent vs reproducible, recent kernel update,
hub/dock hardware, etc.).
