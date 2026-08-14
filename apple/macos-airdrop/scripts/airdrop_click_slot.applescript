-- airdrop_click_slot.applescript <slot_index>
-- Click the Nth recipient (1-based, left-to-right) in an already-open AirDrop picker.
-- Picker must have been launched by ~/Library/Hermes/airdrop or `swift airdrop.swift`.
-- Auto-detects the hosting process name (`airdrop` or `swift-frontend`).
-- Prints "OK clicked slot <N> at <x>,<y>" on success, "ERR ..." on failure.

on run argv
    if (count of argv) < 1 then
        return "ERR: usage: osascript airdrop_click_slot.applescript <slot_index>"
    end if
    set slotIndex to (item 1 of argv) as integer

    -- Detect host process
    set hostProc to ""
    tell application "System Events"
        set names to name of every process whose visible is true
        repeat with n in names
            if (n as string) is "airdrop" then
                set hostProc to "airdrop"
                exit repeat
            end if
        end repeat
        if hostProc is "" then
            repeat with n in names
                if (n as string) is "swift-frontend" then
                    set hostProc to "swift-frontend"
                    exit repeat
                end if
            end repeat
        end if
    end tell
    if hostProc is "" then
        return "ERR: AirDrop picker process not running (looked for airdrop / swift-frontend)"
    end if

    tell application "System Events"
        tell process hostProc
            try
                set win to first window
            on error
                return "ERR: no window in process " & hostProc
            end try

            set recipientButtons to {}
            set uis to entire contents of win
            repeat with elem in uis
                try
                    if role of elem is "AXButton" then
                        set p to position of elem
                        set s to size of elem
                        -- Recipient row heuristic: y in 380..520, width 30..60
                        -- (covers default picker geometry on 13"-16" MBP retina)
                        if (item 2 of p > 380 and item 2 of p < 520 ¬
                            and item 1 of s > 30 and item 1 of s < 60) then
                            copy {item 1 of p, item 2 of p, elem} to end of recipientButtons
                        end if
                    end if
                end try
            end repeat

            -- Selection-sort by x ascending → visual left-to-right
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

            if n is 0 then
                return "ERR: no recipient buttons visible — picker may still be loading or empty"
            end if
            if slotIndex < 1 or slotIndex > n then
                return "ERR: slot " & slotIndex & " out of range (1.." & n & " visible)"
            end if

            set target to item slotIndex of recipientButtons
            click (item 3 of target)
            return "OK clicked slot " & slotIndex & " at " & (item 1 of target) & "," & (item 2 of target) & " (host=" & hostProc & ", " & n & " recipients)"
        end tell
    end tell
end run
