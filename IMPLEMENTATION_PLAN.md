# Download System Implementation Plan

## Current Status
- Downloads DO work (verified in logs)
- Progress callbacks are defined but not being invoked
- UI shows "Preparing download..." and never updates

## Root Cause
The file size monitoring doesn't work because:
1. `hf_hub_download()` downloads to `.cache/huggingface/download/` first
2. We're monitoring the final path, which doesn't exist until download completes
3. The monitoring task keeps looping but never finds the file

## Simple Solution (Immediate)
Remove byte-level monitoring, use simpler per-file updates:
1. Show "Downloading file X of Y" when each file starts
2. Update progress bar after each file completes
3. This is simpler, reliable, and good enough for most use cases

## Implementation
1. Remove `_monitor_file_progress()` complexity
2. Send progress update when file starts
3. Send progress update when file completes
4. Keep the async structure but simplify callbacks

This will make downloads work reliably.
