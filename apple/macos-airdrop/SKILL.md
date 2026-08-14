---
name: macos-airdrop
description: Send files via AirDrop on macOS — open the share sheet programmatically; accept that recipient picking is GUI-only.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [macOS, AirDrop, Sharing, NSSharingService, FileTransfer, Automation]
    related_skills: [imessage, apple-notes]
---

# macOS AirDrop — autonomous send via NSSharingService + accessibility click

AirDrop has no CLI and no `sharingd` public API, so people often assume autonomous send is impossible. It's not. The recipient row in the picker hides *names* (`AXOpaqueProviderGroup`), but the underlying `AXButton` elements are enumerable and clickable through System Events. With a known slot index you get a full hands-off send.

## Fast path (recommended)

```bash
~/.hermes/skills/apple/macos-airdrop/scripts/airdrop_send.sh <file> <recipient-name-or-slot>
```

This wrapper compiles the Swift picker binary if needed, opens the AirDrop window with the file attached, looks up the recipient in `known_recipients.json` (or accepts a 1-based slot index directly), and clicks the right `AXButton` via AppleScript. Returns `OK clicked slot N` on success, status `ERR ...` on failure.

The slot map lives at `~/.hermes/skills/apple/macos-airdrop/known_recipients.json`. Add entries as you confirm them — same Mac, same room, the order stays stable across days.

## When AirDrop is the wrong tool

- Recipient is remote / not nearby → **iMessage** (`imsg send <handle> --attachment <path>`, see `imessage` skill) or `scp` / cloud.
- Recipient on Windows / Linux → AirDrop doesn't reach them; use SMB or cloud.
- Many recipients at once → AirDrop is 1-to-1, use Mail or an iMessage broadcast.

## Why this works (the discovery)

Earlier versions of this skill said recipient picking was impossible. That was based on the (true) observation that the receiver tiles' names are hidden, plus the (false) inference that they couldn't be clicked. They can — `click` in AppleScript dispatches `AXPress`, an accessibility action that goes to the element directly. It needs Accessibility permission (which you already have for `osascript`), not Screen Recording, and doesn't care which window is frontmost. The full recipe is in `references/applescript-recipient-click.md`.

## Prerequisites

- Sender Mac must have AirDrop discovery on (Control Center → AirDrop → Everyone / Contacts Only).
- Recipient must be discoverable.
- Same Apple ID across devices makes the recipient auto-accept; otherwise they must confirm.
- macOS Accessibility permission for the controlling app (Terminal / iTerm / Hermes) — System Settings → Privacy & Security → Accessibility.

## Method 1 — NSSharingService (recommended, opens AirDrop picker)

Most reliable way to open the AirDrop window with a specific file ready to send. Uses Apple's own `NSSharingService` API.

Write this once to `~/Library/Hermes/airdrop.swift` (or any path):

```swift
import Cocoa

let path = CommandLine.arguments[1]
let url = URL(fileURLWithPath: path)

guard let service = NSSharingService(named: NSSharingService.Name(rawValue: "com.apple.share.AirDrop.send")) else {
    print("AirDrop service unavailable"); exit(1)
}

class D: NSObject, NSSharingServiceDelegate {
    func sharingService(_ s: NSSharingService, didFailToShareItems items: [Any], error: Error) {
        print("FAIL: \(error.localizedDescription)"); NSApplication.shared.terminate(nil)
    }
    func sharingService(_ s: NSSharingService, didShareItems items: [Any]) {
        print("SHARED"); NSApplication.shared.terminate(nil)
    }
}
let d = D()
service.delegate = d

let app = NSApplication.shared
app.setActivationPolicy(.regular)
app.activate(ignoringOtherApps: true)

DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
    if service.canPerform(withItems: [url]) {
        service.perform(withItems: [url])
    } else {
        print("cannot perform"); exit(2)
    }
}

app.run()
```

Run it:

```bash
swift ~/Library/Hermes/airdrop.swift /path/to/file.ext
```

The AirDrop window opens, file is attached, user clicks the recipient. Process exits when the user closes the picker or the transfer completes/fails.

**Compile it once for faster repeat use:**

```bash
swiftc ~/Library/Hermes/airdrop.swift -o ~/Library/Hermes/airdrop
~/Library/Hermes/airdrop /path/to/file.ext
```

## Method 2 — Finder Share menu (fallback if Swift unavailable)

```bash
osascript <<'EOF'
tell application "Finder"
    activate
    reveal POSIX file "/path/to/file.ext"
end tell
delay 0.5
tell application "System Events"
    tell process "Finder"
        click menu item "Paylaş…" of menu 1 of menu bar item "Dosya" of menu bar 1
        -- English locale: replace "Paylaş…" with "Share…" and "Dosya" with "File"
    end tell
end tell
EOF
```

Menu item names are LOCALE-DEPENDENT. Check with:

```bash
osascript -e 'tell application "System Events" to tell process "Finder" to return name of every menu bar item of menu bar 1'
```

Turkish: `Dosya / Paylaş…`. English: `File / Share…`. After Share opens, user picks AirDrop submenu, then recipient.

## Method 3 — AppleScript + AXButton enumeration (works, recommended for autonomous send)

The earlier claim that recipient picking is impossible was wrong. `AXOpaqueProviderGroup` hides the *names* of the receiver tiles, but the underlying `AXButton` elements are still enumerable and clickable via System Events. This is the right method when you need a hands-off send and you know the recipient's *position* in the picker (or can ask the user once and remember it).

The full working recipe lives in `references/applescript-recipient-click.md` — read it before automating. Short version:

1. Launch the picker via Method 1 (NSSharingService, the swift binary). The hosting process shows up under `System Events` as `airdrop` (when launched from the compiled binary at `~/Library/Hermes/airdrop`) or `swift-frontend` (when run via `swift script.swift`). Check with `osascript -e 'tell application "System Events" to return name of every process whose visible is true'`.
2. Enumerate buttons: in the picker window, recipient tiles are `AXButton` elements arranged horizontally on a single row, all with the same `y` coordinate (the row top), width ~46–50px, height ~73–84px. Filter by geometry, not by title — titles are all empty.
3. Sort by `x` ascending — that gives you the visual left-to-right order, which matches the order the user sees in the picker.
4. `click` the target element through System Events (this is an accessibility action, NOT a screen click — works without Screen Recording permission and won't be blocked by other windows on top).

Why this is better than `cliclick`:
- No Screen Recording permission needed; only Accessibility for the controlling process.
- Doesn't matter which window is frontmost or which Space is visible.
- Other windows on top of the picker don't block the click — accessibility actions go to the element directly.
- No retina / coordinate-scaling math (cliclick uses logical points, screencapture pixels — easy to get wrong).

Pitfall: recipient *order* in the picker can change between sessions (recency, new devices appearing). If position-based selection feels fragile, ask the user once which slot the target is in and persist it. Apple deliberately denies name introspection — there is no robust way to verify "this button is btekin" purely from accessibility data.

## Inspecting the AirDrop window

The picker runs in the `swift-frontend` host process (when launched via NSSharingService) or Finder otherwise.

```bash
osascript <<'EOF'
tell application "System Events"
    tell process "swift-frontend"
        tell window "AirDrop"
            return entire contents
        end tell
    end tell
end tell
EOF
```

You will see `AXOpaqueProviderGroup` — that's the dead end. The receiver tiles are inside, but their names / positions are not exposed.

## When to choose AirDrop vs alternatives

| Use case | Choice |
|---|---|
| Quick file to nearby Mac/iPhone, user is at the keyboard | AirDrop via Method 1 |
| Fully autonomous send, recipient identity is known | **iMessage** (`imsg send <handle> --attachment <path>`) — see `imessage` skill |
| Long-term remote handoff | Mail attachment via `himalaya` skill, or `scp` / cloud sync |
| Many recipients at once | Mail / iMessage broadcast, AirDrop is 1-to-1 |
| Recipient on Windows/Linux | AirDrop won't work — use SMB, scp, or cloud |

## Pitfalls

1. **Locale matters** for the Finder Share menu path — always probe menu names first.
2. **NSSharingService picker recipient selection is possible via AppleScript AXButton enumeration** (Method 3) — earlier guidance said otherwise, that was wrong. Hands-off send works if you know the recipient's slot index.
3. **Don't trust vision/OCR to read recipient labels.** This skill once sent a file to the wrong device because vision misread the tile label. The recipient *names* in the picker render with a tiny, low-contrast font and OCR routinely mis-identifies similar-looking devices. Always have the user confirm the slot at least once before persisting it to `known_recipients.json`. The AX tree returns empty strings for these tiles by design — vision is the only programmatic way to read them, and it's unreliable.
4. **Same Apple ID auto-accepts**; cross-account always requires recipient tap-to-accept.
5. **Receiver visibility** — if you don't see the target, ask the user to open Control Center → AirDrop on the receiver and set discovery to Everyone.
6. **First-run trust dialog** on the receiver if the two devices have never AirDropped before — adds a delay.
7. **Wi-Fi + Bluetooth both required** on sender and receiver; AirDrop won't fall back to one.
8. **NSSharingService can fail silently if Wi-Fi/BT off** — check console: `log stream --process sharingd`.
9. **Picker can be closed without sending**, NSSharingService still reports success in some cases. Don't rely on the callback as proof of delivery — observe `~/Library/Logs/CrashReporter` or ask the recipient.

## Verification

```bash
# Did transfer happen? Check the recipient's Downloads folder, or recent sharingd logs:
log show --last 5m --predicate 'process == "sharingd"' --info 2>/dev/null | grep -iE 'transfer|completed|accepted'
```
