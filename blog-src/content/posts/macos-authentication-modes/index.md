---
title: "One touch, three paths: how immurok authenticates on macOS"
date: 2026-07-08
description: "macOS has no single API you can plug a fingerprint into. immurok meets each authentication surface with the right mechanism — PAM, credential injection, or a GUI bridge — and keeps a hard security boundary around each. Here's the map, and an honest risk analysis."
tags: ["security", "engineering", "macos"]
slug: "macos-authentication-modes"
---

There is no one place in macOS where you can say "a fingerprint touch counts as the password." `sudo` goes through PAM. The App Store shows its own sheet. Screen unlock is a special world the system guards tightly. "Sign in with Apple" is rendered by a separate helper process. Each surface expects a different kind of proof.

So immurok doesn't have *one* trick — it has three, and it picks the right one per surface. The unifying principle underneath is simple: **the device only ever proves that a real, authenticated touch happened; the host decides what that touch is allowed to unlock.** (How the device proves it — ECDH pairing, HMAC-signed events, biometrics that never leave the sensor — is the subject of [the immurok security model](../the-immurok-security-model/). This post is about the *host* side.)

## One touch, three paths

<svg viewBox="0 0 720 400" role="img" aria-label="A fingerprint touch fans out to three authentication mechanisms" style="max-width:100%;height:auto;font-family:system-ui,-apple-system,sans-serif">
  <defs>
    <marker id="ar" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#94a3b8"/>
    </marker>
  </defs>
  <rect x="230" y="16" width="260" height="54" rx="10" fill="#eef2ff" stroke="#4f46e5"/>
  <text x="360" y="40" text-anchor="middle" font-size="14" font-weight="700" fill="#1e293b">A fingerprint touch</text>
  <text x="360" y="58" text-anchor="middle" font-size="11.5" fill="#64748b">HMAC-signed by your paired device</text>
  <path d="M360,70 L120,104" stroke="#94a3b8" fill="none" marker-end="url(#ar)"/>
  <path d="M360,70 L360,104" stroke="#94a3b8" fill="none" marker-end="url(#ar)"/>
  <path d="M360,70 L600,104" stroke="#94a3b8" fill="none" marker-end="url(#ar)"/>
  <!-- Path A: PAM -->
  <rect x="20" y="108" width="200" height="52" rx="8" fill="#ccfbf1" stroke="#0d9488"/>
  <text x="120" y="132" text-anchor="middle" font-size="13.5" font-weight="700" fill="#134e4a">PAM + BLE</text>
  <text x="120" y="149" text-anchor="middle" font-size="11.5" fill="#0f766e">the device proves it</text>
  <text x="120" y="192" text-anchor="middle" font-size="12" fill="#475569">sudo</text>
  <text x="120" y="210" text-anchor="middle" font-size="12" fill="#475569">ssh-agent signing</text>
  <text x="120" y="228" text-anchor="middle" font-size="12" fill="#475569">GUI authorization</text>
  <!-- Path B: injection -->
  <rect x="260" y="108" width="200" height="52" rx="8" fill="#e0e7ff" stroke="#4f46e5"/>
  <text x="360" y="132" text-anchor="middle" font-size="13.5" font-weight="700" fill="#312e81">Credential injection</text>
  <text x="360" y="149" text-anchor="middle" font-size="11.5" fill="#4338ca">the host fills the field</text>
  <text x="360" y="192" text-anchor="middle" font-size="12" fill="#475569">App Store</text>
  <text x="360" y="210" text-anchor="middle" font-size="12" fill="#475569">Passwords</text>
  <text x="360" y="228" text-anchor="middle" font-size="12" fill="#475569">Sign in with Apple</text>
  <!-- Path C: bridge -->
  <rect x="500" y="108" width="200" height="52" rx="8" fill="#fef3c7" stroke="#d97706"/>
  <text x="600" y="132" text-anchor="middle" font-size="13.5" font-weight="700" fill="#78350f">HID / GUI bridge</text>
  <text x="600" y="149" text-anchor="middle" font-size="11.5" fill="#b45309">host types or submits</text>
  <text x="600" y="192" text-anchor="middle" font-size="12" fill="#475569">screen unlock</text>
  <text x="600" y="210" text-anchor="middle" font-size="12" fill="#475569">SecurityAgent dialogs</text>
  <line x1="40" y1="262" x2="680" y2="262" stroke="#e2e8f0"/>
  <text x="360" y="284" text-anchor="middle" font-size="11.5" fill="#94a3b8">macOS decides what each touch unlocks — immurok only supplies the proof or the secret</text>
</svg>

### Path 1 — PAM + BLE: the device proves it

`sudo`, SSH key signing, and the system's GUI *authorization* prompts all run a PAM stack. immurok ships a tiny module, `pam_immurok.so`, that sits at the front of the relevant `/etc/pam.d` services. When one of them authenticates, the module opens a Unix socket to the companion app, which asks your paired device for a challenge-response over BLE. Touch the sensor, the device returns a signed OK, PAM succeeds.

The important part: **no password is involved anywhere.** The credential *is* the cryptographically signed touch. There is nothing to store and nothing to type.

### Path 2 — Credential injection: the host fills the field

The App Store, the Passwords app, and Safari's "Sign in with Apple" sheet don't go through PAM. They put a real secure text field on screen and wait for you to type. immurok watches the system's focused accessibility element; when a whitelisted app focuses an `AXSecureTextField`, immurok writes the stored secret straight into it through the accessibility API and presses the sheet's confirm button.

Two subtleties make this safe *and* possible:

- It writes the **value** (`kAXValue`), it doesn't synthesize keystrokes — so macOS's Secure Event Input, which blocks fake typing into password fields, doesn't apply.
- The secret it writes lives in the **Keychain** (your login password, or your Apple ID password), never on the device and never over BLE.

### Path 3 — The GUI bridge: host submits, PAM proves

Some GUI dialogs (the standalone SecurityAgent window) *do* run PAM, but only after a human clicks a button. immurok bridges the gap: on a touch it arms a short **pre-authorization** window scoped to the `authorization` service, then submits the field so the PAM chain runs and the pre-auth answers it. Screen unlock is the extreme case — PAM can't dismiss a locked screen at all — so there the device simply types your password over its BLE HID keyboard.

## Where the credential lives

The three paths differ most in one thing that matters for security: **whether a real secret sits on your Mac at all.**

<svg viewBox="0 0 720 260" role="img" aria-label="PAM path stores no secret; injection path stores a secret in the Keychain" style="max-width:100%;height:auto;font-family:system-ui,-apple-system,sans-serif">
  <defs>
    <marker id="ar2" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#94a3b8"/>
    </marker>
  </defs>
  <!-- Lane A -->
  <text x="24" y="34" font-size="12.5" font-weight="700" fill="#0f766e">PAM path</text>
  <rect x="24" y="44" width="150" height="44" rx="8" fill="#ccfbf1" stroke="#0d9488"/>
  <text x="99" y="64" text-anchor="middle" font-size="11.5" fill="#134e4a">device</text>
  <text x="99" y="80" text-anchor="middle" font-size="10.5" fill="#0f766e">touch + HMAC</text>
  <path d="M176,66 L214,66" stroke="#94a3b8" marker-end="url(#ar2)"/>
  <rect x="216" y="44" width="150" height="44" rx="8" fill="#f8fafc" stroke="#94a3b8"/>
  <text x="291" y="70" text-anchor="middle" font-size="11.5" fill="#475569">companion app</text>
  <path d="M368,66 L406,66" stroke="#94a3b8" marker-end="url(#ar2)"/>
  <rect x="408" y="44" width="150" height="44" rx="8" fill="#f8fafc" stroke="#94a3b8"/>
  <text x="483" y="70" text-anchor="middle" font-size="11.5" fill="#475569">PAM stack</text>
  <text x="576" y="60" font-size="11.5" fill="#16a34a">✓ nothing stored</text>
  <text x="576" y="76" font-size="11.5" fill="#16a34a">on disk</text>
  <!-- Lane B -->
  <text x="24" y="150" font-size="12.5" font-weight="700" fill="#4338ca">Injection path</text>
  <rect x="24" y="160" width="150" height="44" rx="8" fill="#e0e7ff" stroke="#4f46e5"/>
  <text x="99" y="180" text-anchor="middle" font-size="11.5" fill="#312e81">Keychain</text>
  <text x="99" y="196" text-anchor="middle" font-size="10.5" fill="#4338ca">login / Apple ID pw</text>
  <path d="M176,182 L214,182" stroke="#94a3b8" marker-end="url(#ar2)"/>
  <rect x="216" y="160" width="150" height="44" rx="8" fill="#f8fafc" stroke="#94a3b8"/>
  <text x="291" y="186" text-anchor="middle" font-size="11.5" fill="#475569">companion app</text>
  <path d="M368,182 L406,182" stroke="#94a3b8" marker-end="url(#ar2)"/>
  <rect x="408" y="160" width="150" height="44" rx="8" fill="#f8fafc" stroke="#94a3b8"/>
  <text x="483" y="186" text-anchor="middle" font-size="11.5" fill="#475569">secure field</text>
  <text x="576" y="176" font-size="11.5" fill="#b45309">▲ a real secret</text>
  <text x="576" y="192" font-size="11.5" fill="#b45309">lives on the host</text>
</svg>

The PAM path stores nothing — that's its great property. The injection path buys convenience on surfaces PAM can't reach, at the cost of keeping an actual password on the machine. immurok narrows that cost deliberately: secrets go in the Keychain, are captured only when you enable the feature, and are wiped the moment you turn it off.

## Security boundaries

Every path is gated so that authority is never granted without explicit, scoped, signed intent.

| Path | Credential on host | Anti-abuse gates |
|---|---|---|
| **PAM + BLE** | none | socket peer must be root or you; each service has its own enable toggle; one auth at a time; auth triggered by an *AI agent* raises an on-screen overlay you can reject; the device must have passed challenge-response verification |
| **Injection** | login / Apple ID password (Keychain) | target matched by bundle id **and** code signature (`anchor apple and identifier …`), so a look-alike app can't impersonate the App Store; feature-gated; only writes into an Apple-signed secure field |
| **GUI bridge / HID** | login password (typed by device), or none | pre-authorization is service-scoped, single-use, and expires in seconds; it only arms when a password field is actually focused — never a blanket "authorize anything" |

Two cross-cutting rules keep the paths from stepping on each other:

- **PAM always wins.** If a PAM request is pending, injection is suppressed — the safer, secret-free path takes priority.
- **No context, no authority.** A touch with no recognizable authentication UI in front of it grants nothing. immurok would rather do nothing than authorize the wrong thing.

## Honest risk analysis

- **Injection leans on an OS behavior Apple could restrict.** Writing a value into a secure field via accessibility is allowed today; a future macOS could lock it down. That's why the device keeps a keyboard: HID typing is the fallback, and the pure-PAM paths don't depend on it at all.
- **The code-signature check is the anti-spoofing anchor.** Matching bundle id alone would be forgeable; requiring `anchor apple` on the target's *running* process is what stops a malicious app from posing as a trusted one to harvest an injected secret.
- **A stored secret is a new local attack surface.** The injection paths trade the PAM path's "nothing on disk" property for reach. Keychain storage, on-demand capture, and clear-on-disable shrink the window, but a compromised host with the feature on can recover those secrets — a pure-PAM setup can't.
- **The pre-auth window is a small race surface.** Scoping it to one service, making it single-use, timing it out in seconds, and requiring a focused password field keep it tight, but it is the one moment where a same-UID process could try to slip in. We keep it as narrow as the UX allows.

The takeaway is the same principle we started with, now with teeth: **prove where macOS lets us, fill where it doesn't, and never hand out authority without explicit, scoped, signed intent.**
