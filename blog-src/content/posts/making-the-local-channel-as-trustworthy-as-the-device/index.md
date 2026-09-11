---
title: "Making the local channel as trustworthy as the device"
date: 2026-09-06
description: "The device signs every touch. The last hop, from the app to sudo, used to trust a plain local socket. This September update closes that gap on macOS, Linux and Windows, and each platform needed a different approach."
tags: ["security", "engineering"]
slug: "making-the-local-channel-as-trustworthy-as-the-device"
---

This is a dev log about the September hardening work. The device side of immurok has been solid for a while: every touch is signed, keys never leave the hardware. The weak spot was the last hop on the computer, where the app tells sudo "this person is here". We have known about it since the early builds and had it on the list. A few people on our Discord asked about exactly this, and we finally had the time to do it properly. The fix ended up different on each platform, for reasons worth writing down.

## The setup

immurok does one thing: a finger touches the device, the device signs a statement saying so. The app checks the signature and tells the system "this person is here".

On macOS and Linux that mostly means PAM. When you run `sudo`, our module `pam_immurok` runs inside sudo as root. It connects to a local socket owned by the app, sends `AUTH:user:service`, and waits. If the reply starts with `OK`, you are in.

That sentence is the whole problem.

## What was wrong

The socket lived in your home directory, so it was writable by every process running as you. Any of them could do this:

```bash
rm ~/.immurok/pam.sock
nc -lU ~/.immurok/pam.sock    # answer "OK" to anything
```

Then run `sudo`. PAM connects, reads `OK`, returns success. Root, no touch, no password.

The app did check who connected to it. But that is the wrong direction. It stops strangers talking to the real app. It does nothing to stop a stranger *being* the app, because the PAM module never verified who it was talking to.

This is worse than not installing immurok. Without it, malware at least has to trick you into typing a password.

The annoying part: we had already built the hard piece. The device signs every match. The app verifies that signature, then throws it away and sends a plain `OK` to the one component running as root. The trust chain stopped one hop early.

## Why three different fixes

The obvious fix is to make the app prove itself: PAM sends a nonce, the app returns an HMAC, PAM checks it. We did that on macOS. We did not do it on Linux. Windows had the same problem in a completely different shape.

A MAC is only as strong as the place you keep the key, and each OS gives you different tools for hiding a secret from other processes running as the same user.

### macOS: nonce plus HMAC, key in the keychain

The macOS keychain ties access to code signature. A key stored by the signed immurok app cannot be read by another process as you without a system prompt. That is a real boundary, so we built on it.

The app generates a random 32-byte key once per machine and keeps it in the keychain. A one-time step, `imk pam-key install`, copies it as root to `/etc/immurok/pam/<uid>.key`, mode 0600. Then:

- PAM sends `AUTH:user:service:<nonce>`.
- The app replies `OK:<HMAC(key, nonce || user || service)>`.
- PAM recomputes from the root-owned file and compares in constant time.

Binding user and service means a reply for one PAM service cannot be replayed for another. The key has nothing to do with the device, so re-pairing or switching hosts never touches it.

The switch is the root-owned key file. If it exists, a bare `OK` or a bad MAC is a hard deny and gets logged, because at that point it is an attack signal. Wrong permissions on the file also fail closed. Only if the file is absent does the old behaviour apply, so upgrades do not lock anyone out.

Two things bit us in the install step. The installer talks to a user-owned socket too, so a fake app could hand it a fake key. It now checks the code signature of the process on the other end first. And Foundation creates files at 0644 before tightening them. Short window, but real. The key goes to a temp file opened `O_EXCL` at 0600, then renamed.

Not covered: an attacker who can inject into the app process. Closing that needs the device to sign for PAM directly, which is firmware work on our list.

### Linux: no MAC, real privilege separation

We started porting the macOS design and stopped halfway. On Linux the daemon's secrets already sit in a 0600 file in your home directory, readable by anything running as you. There is no keychain. A PAM key next to it is one more file to read. The MAC would only stop the laziest attack.

The only thing that creates a boundary on Linux is running the daemon as someone else. So:

- The daemon moved to a system unit with `User=immurok`, `ProtectHome=yes`, `ProtectSystem=strict`.
- Its binary moved from `~/.local/bin` to `/usr/local/bin`, root-owned.
- The socket moved to `/run/immurok/pam.sock`, in a directory nobody else can write.

Now nobody running as you can replace the socket, and the plain `OK` protocol is safe as it is. The PAM module checks this before connecting: it `lstat`s the directory and refuses if it is user-owned, group-writable, or a symlink.

One machine-wide socket raises a new question: who may ask for what? The daemon reads `SO_PEERCRED` and applies rules per command. `AUTH` only from root and polkitd. Status for anyone. Anything touching the device or secrets needs an active login session on this machine, checked through logind. The daemon also records which user paired the device, so a second account on the same box cannot ride the owner's touch through `sudo`.

The "touch now" prompt is drawn by a small helper inside your session. It sits outside the boundary on purpose. Kill it or fake it and you lose the dialog. You never gain an approval.

### Windows: the same problem in four shapes

On Windows the service already runs as SYSTEM and talks to the device itself. No root-trusts-user hop. But the same class of issue showed up in four other places.

**The credential provider pipe.** At the lock screen the service writes your Windows password into a named pipe that LogonUI reads. Pipe names are global and first come, first served, and the credential provider only creates it at lock time. Between login and lock, any user process could create that name and wait. Fix: before writing, the service checks that the other end runs as SYSTEM, is LogonUI, and belongs to the console session being unlocked.

**Pipe instances.** The service's pipes let Authenticated Users create new instances, so any process could receive commands meant for the service, including the one that sets the login password. That right is gone, and the first instance is created with `FirstPipeInstance`.

**Who is calling.** The service did not identify callers. Anyone could clear the login password or disable protections. It now checks the caller's image path and signature. But a process running as you can inject into our own client and send commands from inside it, so this is defense in depth, not a boundary. The boundary is the device. The two commands that write something lasting, setting the login password and pushing firmware, now need a fresh fingerprint on the device. Feature toggles do not. A toggle never releases a secret by itself; unlocking, SSH signing and reading an OTP each still need a touch, so gating the toggle would only mean touching twice.

The service also records the SID of the user who paired, and we learned the hard way how much that matters. Our first version only gated secret reads on the fingerprint, on the theory that a touch is consent no matter who asks. Then we tested with a second standard account. Switch users, and the first account's processes keep running in the background. One of them can wait for the owner to touch the device and read secrets on the owner's ticket. So reading an OTP, an API key, or the key list now checks the owner SID before anything goes to the device, and a non-owner gets a clear `DENY:NOT_OWNER` instead of a silent failure.

**Keys on disk.** The pairing key used DPAPI at machine scope, which any process on the machine can undo. It is now user scope under SYSTEM, and the data directory is locked to SYSTEM and Administrators. Surprise along the way: `CryptUnprotectData` ignores the scope you pass and reads it from the blob, so "try user scope, fall back to machine" silently never migrated anything. The file now carries a format header.

## Still open

Two things are shared by all three platforms and not fixed yet.

The device's fingerprint gate has a ten second cooldown that refreshes on every use. A process that polls faster than that can keep one real touch alive forever and drain every OTP and API secret. Windows now caps this on the host side and checks the owner before every read. The proper fix is for the host to declare a budget when it asks for authorization, and that is firmware.

And the device does not authenticate the host. Anything with Bluetooth access can ask it to light up and wait for a touch. Without a screen on the device, that is a limit of the form factor.

## Where things stand

- macOS: merged, ships with the next app and PAM package release. Strong mode turns on from the settings page.
- Linux: shipped in 0.6.0. `make install` migrates an existing setup in one step.
- Windows: shipped in 0.5.0. Everything above was tested on a real machine, including the second-account case. The one path we still want to run in a VM is upgrading while the console sits at the lock screen, because the credential provider is loaded inside LogonUI and a bad swap there means a broken login screen.

If you find something like this in our code, we would rather hear about it than not: support@immurok.com.
