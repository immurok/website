---
title: "Why we're building immurok"
date: 2026-03-06
description: "Millions of developers use desktop Macs and Linux machines without any biometric auth. We're building a tiny wireless fingerprint key to fix that."
tags: ["announcement"]
slug: "why-we-are-building-immurok"
---

If you use a Mac mini, Mac Studio, or a MacBook in clamshell mode with an external keyboard, you know the pain: **no Touch ID**. Apple's only solution is a $199 Magic Keyboard — and if you prefer a mechanical keyboard, you're completely out of luck.

Linux users have it even worse. `fprintd` exists, but good hardware options are scarce.

## The problem

Every time you:

- Unlock your screen
- Run `sudo`
- Approve a system dialog
- Sign a Git commit

...you type a password. Dozens of times a day.

## Our solution

immurok is a tiny wireless device with a capacitive fingerprint sensor. It connects via Bluetooth LE and replaces passwords with a single touch:

- **Screen unlock** — touch the sensor, screen unlocks
- **sudo & PAM** — custom PAM module intercepts auth prompts
- **SSH agent** — sign commits and SSH into servers with your fingerprint
- **Open source** — the macOS app and PAM module are fully auditable

## Security first

Your fingerprint template never leaves the device. Authentication uses ECDH P-256 key exchange and HMAC-SHA256 signed messages. There's no cloud, no account, no telemetry — everything works offline over Bluetooth.

We'll be sharing more technical deep-dives on the BLE protocol, PAM integration, and firmware architecture in upcoming posts. Stay tuned.
