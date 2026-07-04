---
title: "The immurok security model"
date: 2026-05-28
description: "A fingerprint key is only as good as the trust it can prove. Here's how immurok keeps your biometrics on the device, authenticates every touch, and refuses to phone home — ECDH pairing, HMAC-signed events, and signed firmware, end to end."
tags: ["security", "engineering"]
slug: "the-immurok-security-model"
---

immurok replaces your password with a fingerprint. That only works if the fingerprint touch is something your Mac can *trust* — not just a button press that any nearby radio could fake. This post is the full picture of how that trust is built: what the device proves, what the host verifies, where keys live, and the things we deliberately refuse to do.

## The threat model

We designed against a concrete set of attackers:

- **A passive radio eavesdropper** sniffing Bluetooth LE traffic in the room.
- **An active attacker** who can connect to the device, spoof advertisements, or replay captured packets.
- **A malicious or compromised peripheral** pretending to be your immurok key.
- **A thief** who walks off with the device itself.
- **A supply-chain attacker** trying to push tampered firmware onto the device over the air.

And a set of principles we hold regardless of attacker:

1. **Your biometric never leaves the sensor.** Not over BLE, not to disk, not to a cloud.
2. **Every authentication event is cryptographically authenticated** — a touch the host accepts must have come from *your* paired device.
3. **No cloud, no account, no telemetry.** The entire system works offline. There is no server to breach because there is no server.
4. **The host is the policy engine; the device is the proof.** macOS decides *what* a touch unlocks; the device only proves *that* a real, authenticated touch happened.

## Biometrics stay on the device

The fingerprint sensor (an R559S capacitive module) does matching *on-chip*. Enrollment templates are stored in the sensor's own flash and are never read out over the wire. The CH592F microcontroller that runs immurok's firmware never sees your fingerprint image or template — it only ever receives a match result: *page N matched*, or *no match*.

That means the BLE link, the companion app, your Mac's disk, and certainly our infrastructure (which doesn't exist for this) never hold anything that could reconstruct a fingerprint. The worst case for a stolen device is a stolen device — not a stolen identity.

Matching strictness matters here too. The sensor exposes a configurable score threshold, and the firmware sets it explicitly rather than trusting a vendor default. We learned this the hard way: an early build left the score level unset, fell back to the module's lax default, and a second validation step was missing in firmware — which let unenrolled fingers occasionally pass. The fix (firmware 1.3.14) pins the score level *and* re-validates the match index in firmware before signing anything. Biometric thresholds are now part of the build, not an accident of defaults.

## Pairing: ECDH, once

When you pair a device, the app and the device run an **ECDH key agreement over NIST P-256**:

1. The app generates an ephemeral P-256 key pair and sends its compressed public key (33 bytes) to the device.
2. The device does the same and sends its public key back.
3. Both sides compute the shared secret, then run it through **HKDF-SHA256** (with a fixed salt and info string) to derive a 32-byte symmetric **shared key**.

```swift
let sharedSecret = try privateKey.sharedSecretFromKeyAgreement(with: devicePubKey)
let symmetricKey = sharedSecret.hkdfDerivedSymmetricKey(
    using: SHA256.self,
    salt: "immurok-pairing-salt",
    sharedInfo: "immurok-shared-key",
    outputByteCount: 32
)
```

The shared key never crosses the wire — each side derives it independently from the key agreement. The ephemeral private key is discarded the moment pairing completes. From then on, the app and the device share one secret that proves they paired with *each other*.

This is a single-device design on purpose: one key, one device, no roaming credentials to manage or leak.

## Every touch is signed

A fingerprint match isn't a bare "OK" byte that anyone could forge. When the device confirms a match, it emits a **signed match notification** over the custom GATT characteristic:

```
[0x21][page_id : 2 bytes][HMAC-SHA256(shared_key, 0x21‖page_id) : 8 bytes]
```

The app recomputes the HMAC with its copy of the shared key and rejects the notification unless the tag matches exactly. An attacker who can write arbitrary GATT values can't produce a valid tag without the shared key — and the shared key was never transmitted. A forged or replayed-from-a-different-device "match" simply fails verification and is dropped.

On top of per-event signing, the app runs a **challenge–response** check when it (re)connects to a device, to make sure it's still talking to the real key and not a clone or impostor advertising the same name:

1. The app generates a fresh 8-byte random nonce.
2. The device replies with `HMAC-SHA256(shared_key, nonce)[0:8]`.
3. Only a device holding the shared key can answer correctly.

A device that passes is cached as *verified* (by its BLE identifier) so the check is cheap on subsequent connects, and the cache is cleared whenever you unpair.

## Why a HID keyboard *and* a custom protocol

immurok presents itself to the system as a **BLE HID keyboard**. That's not the security channel — it's the *connection anchor*. Operating systems aggressively maintain connections to HID keyboards, which is what lets a tiny battery-powered key stay reliably reachable without a background daemon hammering the radio. This is the same on macOS and Linux — the host OS isn't special-cased; both treat the device as a keyboard and keep it alive.

All the actual authentication traffic — pairing, signed match events, challenge–response — runs over a **separate custom GATT service**. We use purely random 128-bit UUIDs for that service, deliberately steering clear of the Bluetooth SIG's reserved ranges and the Bluetooth Base UUID space, so our private protocol never collides with or impersonates a standardized service.

Splitting the roles this way means the convenient, always-connected HID surface carries no secrets, and the secret-bearing surface is a private protocol that a generic BLE client has no reason — and no schema — to poke at.

## Where keys and secrets live

It's worth being precise about which secrets live where, because it's easy to assume "the app stores my secrets." It doesn't.

**Your high-value secrets live on the device.** SSH keys, OTP seeds, and API keys behind `imk://` URIs are stored in the device's own protected storage. They're released only momentarily — into a child process's environment at `exec()` time, under an active fingerprint cooldown — and are never written to the host's disk, never held by the parent shell, and never land in an agent's transcript. The device is the vault.

**The host only holds pairing material.** On macOS, the shared key and the verified-device record live in the **Keychain** as generic password items, with `kSecAttrAccessibleAfterFirstUnlock` — readable only after the user has unlocked the Mac once since boot, and never synced off the machine. That's the pairing secret that proves *this* Mac paired with *your* device; it is not your SSH key or your API keys.

**The one host-stored password is the screen-unlock password — and only on macOS.** This is where the two platforms diverge. On **Linux**, the lock screen goes through PAM like everything else, so screen unlock rides the same PAM path as `sudo` — *no stored password at all*, just a verified touch satisfying the auth prompt. On **macOS**, the lock screen *can't* be dismissed by PAM (the macOS login window and screensaver don't consult third-party PAM modules), so for that one flow we fall back to keyboard simulation: the app keeps your login password in the Keychain and types it via simulated keystrokes after — and only after — it has verified a signed match from your device. Even in that fallback the password is at rest in the OS keystore, gated behind a cryptographically verified touch, and never crosses the wire. This applies to screen unlock alone — nothing else stashes a password on the host.

## The agent gate, briefly

The same trust primitives back immurok's gate for AI coding agents: when an agent wraps a command with `imk run --agent --`, a single verified fingerprint touch brokers `sudo`, SSH signing, and secret reads for the lifetime of that one subprocess, and a rejection cleanly kills it. The fingerprint *is* the human-in-the-loop signature. We wrote that flow up in detail in [A fingerprint gate for your AI coding agent](/blog/fingerprint-gate-for-ai-agents/) — the relevant point here is that it's built on the very same signed-touch foundation, not a separate trust path.

## Firmware can't be tampered with over the air

A wireless device that accepts wireless firmware updates is a juicy target. immurok's OTA pipeline is built so that only firmware *we* built will ever boot:

- Each update image is **encrypted with AES-128** and carries an **HMAC-SHA256 signature** plus a SHA-256 integrity hash.
- Those keys are generated per developer-machine (`generate_ota_keys.py`) and **never committed to git** — they're baked into the firmware build and the packaging tool.
- Before committing an update, the device verifies the integrity hash *and* the signature. An image that fails either is rejected as **unofficial firmware** and discarded — it never gets promoted to the boot slot.

The update itself uses a dual-image (A/B) layout with a tiny separate bootloader (IAP): the new image is written to the inactive slot, verified, and only then swapped in. A failed or tampered update leaves the running firmware untouched.

## When the attacker has the device in hand

Everything above assumes the attacker is on the radio. But a fingerprint key is a small object that lives on your desk, and the more interesting attacks happen once someone is holding it. We treat physical possession as its own threat, with two layers.

**A stolen device can't be re-paired.** The moment a device has a saved shared key, the firmware flips its BLE bonding policy to refuse new bond requests. A thief can't simply walk the device over to their own machine and pair it — the pairing slot is already claimed, and there's no "forget and re-pair" path that doesn't go through a wipe first.

**Opening the case wipes the device.** This is the one that matters if the attacker decides to get physical — desolder the flash, attach a debugger, probe the bus to extract keys. A spring contact inside the enclosure is wired to a tamper line on the microcontroller. Cracking the case open trips a hardware interrupt, and the firmware immediately erases everything that has value:

1. the pairing shared key and the on-device keystore (your SSH keys, OTP seeds, and API secrets),
2. all BLE bonds,
3. every enrolled fingerprint template.

Then it lights a solid red LED, shuts off the radio, and halts until the device is power-cycled. By the time anyone has the case open far enough to touch the flash, there's nothing left on it.

The part that took the most care is making the wipe **un-interruptible**. The obvious attack is to pop the case and immediately cut power, hoping to freeze the chip mid-erase with secrets still intact. So the wipe is a transaction: before erasing a single byte, the firmware writes a `case_opened` marker to a reserved flash page. If power is lost halfway through, the *next* boot sees that marker still set and resumes the wipe before doing anything else. The marker is cleared only after the erase fully completes. You cannot win the race by yanking the battery.

Getting the detection itself reliable was its own small saga. The tamper line is read as a high-impedance signal (an open case pulls it to ~3 V through a high-value divider), so the pin has to be a true floating input — an early build that enabled the chip's internal pull-down crushed the open-case signal down to 0.23 V and missed it entirely. Boot also deliberately checks only the stored marker, not the live line, so a case that's open on the assembly bench during flashing still boots normally; it's the *act of opening* a sealed unit that trips the wipe, not the static state.

This hardware tamper response ships on the latest revision (validated June 2026).

## What we deliberately don't do

Security is as much about absence as presence:

- **No cloud and no account.** There's no backend that could be breached, no credential database, no password-reset flow to socially engineer.
- **No telemetry.** The device and app don't report usage anywhere.
- **We don't touch `authorizationdb`.** macOS's authorization database governs deeply sensitive system rights; immurok integrates through PAM and the screen-unlock path and leaves that subsystem alone entirely.
- **Open and auditable.** The hardware design, the macOS app, the PAM module, and the Linux app are all open source. The firmware will be opened up before the end of the year — we're holding it back only long enough to protect against cheap clones at launch, not to hide anything. The crypto described here isn't a marketing claim you have to take on faith — it's `CryptoKit` calls you can read in `ImmurokSecurity.swift`.

## The short version

Your fingerprint stays on the sensor. Pairing derives a shared key over ECDH that never crosses the wire. Every touch your Mac accepts carries an HMAC tag only your device could produce, and the device proves itself with a fresh challenge on every connect. Keys rest in the Keychain; firmware updates are encrypted and signed; nothing phones home. That's the whole model — small enough to fit on a chip with 26 KB of RAM, and strong enough that the worst outcome of losing the device is buying another one.

We'll keep publishing the details as the protocol evolves. If you want to read the code first, the [hardware design, macOS app, PAM module, and Linux app are on GitHub](https://github.com/immurok) — with the firmware to follow before year's end.
