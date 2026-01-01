# Pause/Resume User Guide

**Version:** 1.0
**Last Updated:** 2026-01-01
**Feature:** Processing interruption and recovery

---

## Overview

The pause/resume feature allows you to pause transcript processing at any time and resume it later without losing progress. Perfect for long transcripts or when you need to stop processing due to interruptions.

### What You Can Do

- **Pause Anytime**: Stop processing with the Pause button during active processing
- **Resume Later**: Come back to the same transcript and continue where you left off
- **Auto-Resume**: When restarting the app with incomplete work, you'll be prompted to resume or start fresh
- **Track Progress**: See real-time progress with chunk-level granularity
- **No Data Loss**: All progress is saved locally; completed chunks are cached

---

## Quick Start

### Pausing Active Processing

1. **During Processing**: Click the **"Pause"** button in the UI
   - Processing will complete the current chunk before pausing
   - Your progress is automatically saved
   - Status changes to "Paused"

2. **After Pause**: You can either
   - **Resume**: Click "Resume" to continue from where you left off
   - **Start Fresh**: Close the app or click "New Processing"

### Auto-Resume on Restart

1. **Incomplete Job Detected**: When you reopen the app with incomplete work
2. **Resume Prompt**: A notification appears showing:
   - File name and title
   - Progress (e.g., "10/50 chunks completed")
   - Failed chunks count (if any)
   - Cost tracking (estimated vs actual spent)

3. **Choose Your Action**:
   - Click **"Resume Processing"** to continue
   - Click **"Start Fresh"** to discard and restart

---

## UI Features

### Resume Prompt (Displayed on Startup)

```
🔄 Incomplete processing job found

📊 Job Details:
File: lecture-20250101.srt
Progress: 10/50 chunks
Status: PAUSED
Failed Chunks: 0
Estimated Cost: $0.1200
Actual Cost: $0.0450

[Resume Processing] [Start Fresh]
```

**Information Provided:**
- **File**: Name of the transcript file being processed
- **Progress**: Number of completed chunks vs total
- **Status**: Current state (PAUSED, PROCESSING, etc.)
- **Failed Chunks**: Number of chunks that failed (usually 0)
- **Cost Tracking**: Estimated cost vs amount already spent

### Progress Display During Processing

```
Processing: 15/50 chunks (30%)
[████████░░░░░░░░░░░░░░] 30%

Current Status: Processing chunk 15 of 50
Time Elapsed: 2m 30s
Estimated Time Remaining: 5m 45s

[Pause] [Cancel]
```

**Visible Information:**
- Current/total chunks processed
- Percentage complete
- Progress bar
- Time tracking
- Pause/cancel buttons

---

## How State Persistence Works

### What Gets Saved

The app saves processing state to a local JSON file after each chunk:

```json
{
  "file_id": "abc123def456",
  "file_name": "lecture-20250101.srt",
  "video_title": "Introduction to Machine Learning",
  "status": "paused",
  "started_at": "2026-01-01T10:30:00+00:00",
  "last_updated": "2026-01-01T10:35:45+00:00",

  "total_chunks": 50,
  "completed_chunks": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  "failed_chunks": {},

  "processed_results": [
    {
      "chunk_index": 0,
      "original_text": "...",
      "cleaned_text": "...",
      "input_tokens": 450,
      "output_tokens": 320,
      "cost": 0.0045,
      "model": "claude-3-5-sonnet-20241022",
      "provider": "anthropic"
    }
    // ... more results
  ],

  "estimated_cost": 0.1200,
  "actual_cost": 0.0450,
  "total_input_tokens": 4500,
  "total_output_tokens": 3200
}
```

**Saved Information:**
- Unique file identifier (hash-based)
- File and video metadata
- Processing status (idle, processing, paused, completed, crashed)
- Timestamps (start time, last update)
- Progress (completed chunks, failed chunks)
- Results cache (all cleaned chunks)
- Cost metrics (estimated vs actual)

### Where State Is Stored

Files are stored locally in: `output/.processing/`

- **State File**: `processing_state.json` (main state)
- **Backup File**: `processing_state.backup.json` (for recovery)
- **Lock File**: `.processing_state.lock` (prevents concurrent access)

**Security Note**: State files are stored locally only; they're never sent to any server.

---

## Workflow Examples

### Example 1: Simple Pause & Resume

```
1. Start new processing
   └─> Status: "processing"

2. 20 chunks completed
   └─> Click "Pause" button

3. Status changes to "paused"
   └─> Progress saved: 20/50 chunks

4. Close app (or do other work)

5. Reopen app
   └─> See "Resume Processing" button

6. Click "Resume Processing"
   └─> Processing continues from chunk 21
   └─> No re-processing of chunks 0-20

7. Remaining 30 chunks processed
   └─> Final output generated
```

### Example 2: Network Failure Recovery

```
1. Processing 30/50 chunks
   └─> Network error occurs

2. App detects error, marks state as "crashed"
   └─> Error details shown to user

3. Close app

4. Fix network issue

5. Reopen app
   └─> Resume prompt appears

6. Click "Resume Processing"
   └─> Resume from chunk 30 (not reprocessing 0-29)
   └─> Continue processing with restored network
```

### Example 3: Interrupted by Computer Sleep

```
1. Processing 25/50 chunks
   └─> Computer goes to sleep (pause/resume automatic)

2. Resume computer
   └─> Check app

3. Processing may continue or pause gracefully

4. Next app session shows resume option
   └─> Click "Resume Processing"
   └─> Continue from chunk 25
```

---

## Cost Tracking

### Estimated vs Actual Cost

The UI shows both estimated and actual costs:

- **Estimated Cost**: Calculated before processing starts
- **Actual Cost**: Tracked as chunks are processed
- **Savings**: Shows how pause/resume saves money

**Example:**
```
Estimated Cost: $0.1200
Actual Cost After Pause: $0.0450
Cost to Complete: ~$0.0750

Resume will cost approximately $0.0750 more
Total when complete: ~$0.1200
```

### Why Pause/Resume Saves Money

1. **Failed Chunks Skipped**: Already-failed chunks aren't retried
2. **Partial Processing**: Only pay for chunks actually processed
3. **Better Planning**: See costs before continuing

---

## Troubleshooting

### Issue: "Resume not available" after closing

**Cause**: State file was deleted or corrupted

**Solution**: Click "Start Fresh" and process the entire transcript again

---

### Issue: "Chunks showing as completed but not in output"

**Cause**: Processing was paused before completion; results not written to file

**Solution**: Click "Resume Processing" to finish, then output will be generated

---

### Issue: "Different progress shown on different devices"

**Cause**: State file is device-specific (local storage only)

**Solution**: Always use the same device to resume. State files don't sync across devices.

---

### Issue: "Resume button disabled"

**Cause**: State may be complete, crashed, or corrupted

**Solution**: Check job status. If "completed", output file should be ready. If "crashed", state is unrecoverable; start fresh.

---

## Advanced: Manual State Management

### Clearing Saved State

If you want to force a fresh start:

**Via UI**: Click "Start Fresh" button

**Manual**: Delete the state file at `output/.processing/processing_state.json`

### Viewing Raw State

For debugging, you can examine the state file directly:

```bash
cat output/.processing/processing_state.json
```

This shows:
- Current status
- Completed chunks
- Any errors
- Progress metrics
- Cost tracking

---

## Best Practices

### When to Pause

- **Long Transcripts**: Pause every 20-30 chunks to checkpoint
- **Approaching Deadline**: Pause and finish later
- **Cost Monitoring**: Pause to check costs before continuing
- **Network Issues**: Pause if experiencing connectivity problems

### When NOT to Use Pause/Resume

- **Short Transcripts** (<10 min): Just let it run
- **One-time Processing**: No need to pause
- **Multiple Devices**: Process on same device to avoid state conflicts

### Tips for Success

1. **Monitor Progress**: Check progress display regularly
2. **Note Cost**: Use cost tracking to budget your processing
3. **Single Device**: Use the same device for pause/resume
4. **Backup Output**: Once completed, backup the markdown file
5. **Check Failed Chunks**: Review any failed chunks before resuming

---

## Technical Details

### State Machine

```
        ┌──────────┐
        │   idle   │
        └─────┬────┘
              │ start_new_job()
              ▼
        ┌──────────┐
        │processing├────┐
        └─────┬────┘    │
              │         │ process_chunk()
              │ pause() │ + save state
              │         │
              ▼         ▼
        ┌──────────┐  ┌──────────┐
        │  paused  │  │completed │
        └─────┬────┘  └──────────┘
              │
              │ resume()
              ▼
        ┌──────────┐
        │processing│
        └──────────┘

Exception Handling:
        ┌──────────┐
        │processing├────────┐
        └──────────┘        │ fatal error
                            │
                            ▼
                      ┌──────────┐
                      │ crashed  │
                      └──────────┘
```

### Thread Safety

- State writes use file locking (FileLock)
- Atomic writes prevent corruption
- Safe for concurrent access (though single-user typical)

---

## FAQ

**Q: Can I pause on a mobile device and resume on desktop?**
A: No. State files are device-specific. Always use the same device.

**Q: What happens if I force-quit the app during pause?**
A: Your state is saved. When you reopen, resume prompt will appear.

**Q: Can I edit the state file manually?**
A: Not recommended. Edits may cause corruption. Use UI buttons instead.

**Q: How long can paused jobs stay paused?**
A: Indefinitely. No time limit on paused jobs.

**Q: Will pause/resume work with different LLM providers (Claude vs DeepSeek)?**
A: State is provider-specific. If you change providers mid-pause, you may lose cached results.

**Q: What if state file becomes corrupted?**
A: App will try to recover from backup. If both fail, click "Start Fresh".

---

## See Also

- **System Architecture**: `/docs/system-architecture.md` (Phase 7 section)
- **Code Standards**: `/docs/code-standards.md` (State Management section)
- **Main README**: `/README.md` (Features section)
