<!--
Thanks for contributing to usb-devices!

PRs are squash-merged. Your PR title becomes the commit on `main` and drives
python-semantic-release's version bump, so it MUST follow the conventional
commits convention (https://www.conventionalcommits.org). Use a lowercase
subject (the `pr-title` CI job enforces both).

Examples of valid titles:
  feat: add USBDevice.reset() retry on EBUSY
  fix: handle UnicodeDecodeError when sysfs returns non-UTF-8 bytes
  docs: clarify async_reset() return semantics
  chore(deps): bump pytest to 8.3.4
  test: cover OSError paths in BluetoothDevice.reset
-->

## Summary

<!-- One or two sentences: what does this PR change and why? -->

## Changes

<!-- Bullet list of the concrete things this PR does. Skip if the diff is self-explanatory. -->

-

## Testing

<!--
This library talks to real Linux `/sys` and `/dev` nodes via ioctl, so be
explicit about what you actually exercised. If you only ran the unit tests,
say so — that's useful too.
-->

- [ ] `poetry run pytest` passes locally
- [ ] `pre-commit run --all-files` passes locally
- [ ] Tested against a real USB Bluetooth adapter (if applicable — please note model/vendor)

## Notes for reviewers

<!-- Anything non-obvious: design trade-offs, follow-ups, related issues, breaking changes. -->

Closes #
