# AirDrop recipient click via AppleScript — full working recipe

This is the autonomous-send method. Confirmed working on macOS 26.x with the picker launched by NSSharingService.

## Why this works when `cliclick` doesn't

The AirDrop picker's recipient tiles are real `AXButton` elements. Apple hides their `title` and `description` (returns empty / "düğme" / "button"), but `position`, `size`, `role` are all readable, and System Events `click` sends an `AXPress` action that reaches the element regardless of whether the picker is the frontmost window or even visible on the current Space. That sidesteps every problem `cliclick` has:

- No Screen Recording permission required (cliclick + screencapture loop kept tripping the permission dialog mid-task).
- No retina coordinate scaling bugs (screencapture pixels vs cliclick logical points → easy to get 2× wrong).
- Window on top of the picker doesn't matter — accessibility actions don't need pixels.
- Doesn't move the user's cursor.

## Step-by-step

### 1. Launch the picker

Compile the swift binary once for fast reuse:

```bash
swiftc ~/Library/Hermes/airdrop.swift -o ~/Library/Hermes/airdrop
```

Then for each send:

```bash
~/Library/Hermes/airdrop /path/to/file.ext &
sleep 2  # let the picker draw
```

### 2. Find the hosting process name

It depends on how you launched:

- Compiled binary at `~/Library/Hermes/airdrop` → process name is `airdrop`
- Run via `swift script.swift` → process name is `swift-frontend`

Verify before each automation:

```bash
osascript -e 'tell application "System Events" to return name of every process whose visible is true'
```

### 3. Inspect the picker (one-time, to learn geometry)

```applescript
tell application "System Events"
    tell process "airdrop"
        set out to ""
        set win to first window
        set uis to entire contents of win
        repeat with elem in uis
            try
                if role of elem is "AXButton" then
                    set p to position of elem
                    set s to size of elem
                    set out to out & "x=" & (item 1 of p) & " y=" & (item 2 of p) & " w=" & (item 1 of s) & " h=" & (item 2 of s) & linefeed
                end if
            end try
        end repeat
        return out
    end tell
end tell
```

You'll see the recipient row clearly: 5 (or however many) buttons all at the same `y`, widths ~46–50, heights ~73–84, x-spacing ~70px. Below that there's typically one more button (the "Cancel" / "Vazgeç" button) at a different y/size — that's how you know to stop including it.

### 4. Click the target by slot index (1-based, left-to-right)

```applescript
on clickRecipient(slotIndex)
    tell application "System Events"
        tell process "airdrop"
            set win to first window
            set recipientButtons to {}
            set uis to entire contents of win
            repeat with elem in uis
                try
                    if role of elem is "AXButton" then
                        set p to position of elem
                        set s to size of elem
                        -- Recipient row: y in 420..460, width 30..60
                        if (item 2 of p > 420 and item 2 of p < 460 ¬
                            and item 1 of s > 30 and item 1 of s < 60) then
                            copy {item 1 of p, elem} to end of recipientButtons
                        end if
                    end if
                end try
            end repeat
            -- Sort by x ascending (visual left-to-right)
            -- AppleScript has no native sort; use a quick selection sort
            set n to count of recipientButtons
            repeat with i from 1 to n - 1
                set minIdx to i
                repeat with j from i + 1 to n
                    if (item 1 of (item j of recipientButtons)) < (item 1 of (item minIdx of recipientButtons)) then
                        set minIdx to j
                    end if
                end repeat
                if minIdx is not i then
                    set tmp to item i of recipientButtons
                    set item i of recipientButtons to item minIdx of recipientButtons
                    set item minIdx of recipientButtons to tmp
                end if
            end repeat
            if slotIndex > (count of recipientButtons) then
                return "ERR: only " & (count of recipientButtons) & " recipients visible"
            end if
            click (item 2 of (item slotIndex of recipientButtons))
            return "OK clicked slot " & slotIndex
        end tell
    end tell
end clickRecipient

clickRecipient(2)  -- click the 2nd recipient
```

### 5. Verify the send started

After clicking, the chosen tile gets a "Bekleniyor…" / "Waiting…" label underneath. You can confirm by re-dumping the AX tree and looking for a new `AXStaticText` near the clicked button, or by `screencapture` + vision if you have the permission.

The `Bitti` / `Done` button appears in place of `Vazgeç` / `Cancel` when at least one recipient is selected — that's a non-pixel signal you can read from the AX tree.

## Picking the right slot

Apple makes recipient *names* unreadable. Three strategies:

1. **Persist per-recipient slot** — first time, ask the user "btekin which slot?", store `{btekin: 2}` in memory. Most receivers stay put across sessions if the same devices are nearby.
2. **Probe by send + verify** — click slot N, ask the user (Telegram / iMessage) to confirm receipt. If wrong, click `Vazgeç`, retry slot N+1.
3. **Fallback to iMessage** when the recipient has a known Apple ID / phone number — `imsg send <handle> --attachment <path>` is fully autonomous and unambiguous.

For one-shot operations to a specific person, iMessage is more reliable. For "send to whichever Mac is closest" or "send to my phone", AirDrop slot indexing is fine.

## Pitfalls observed during the original session

- **Don't confuse cliclick + screencapture coordinate spaces.** Screencapture returns pixels at the retina resolution (3024×1964 on a 14" MBP); cliclick uses logical points (1512×982). The factor of 2 cost an hour of misclicks.
- **Screen Recording permission dialog steals focus.** First time you call `screencapture -x` the OS pops a permission dialog, which raises and immediately closes the AirDrop picker. Either grant the permission once up-front or skip screencapture entirely (this AppleScript method doesn't need it).
- **Process name changes by launch method** — re-detect with `System Events` if a script worked yesterday and broke today.
- **`set frontmost to true` errors with -10006** on the swift host process. You don't need it — accessibility actions work without bringing the window forward. Locale matters too: on Turkish macOS the error reads `process "airdrop" alınamıyor` / `true olarak ayarlanamıyor` — same root cause, just drop the `set frontmost to true` line.
- **Always run the compiled binary, not the `swift script.swift` interpreter form**, when you plan to drive the picker from AppleScript. With the interpreter, the process is registered as `swift-frontend` and System Events sometimes fails to find it (`process "swift-frontend" alınamıyor`) because it's a short-lived helper that the accessibility subsystem hasn't indexed yet. The compiled binary at `~/Library/Hermes/airdrop` registers immediately under its own name and is reliably enumerable. One-time compile: `swiftc ~/Library/Hermes/airdrop.swift -o ~/Library/Hermes/airdrop`.
