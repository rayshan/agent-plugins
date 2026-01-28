---
name: audio-normalize
description: This skill should be used when the user asks to "normalize audio", "fix audio volume", "make audio louder", "level audio", or provides an audio file for volume normalization. Uses ffmpeg's loudnorm filter for professional two-pass normalization.
argument-hint: [audio-file-path]
---

Normalize audio volume using ffmpeg's two-pass loudnorm filter.

## Process

1. Analyze audio to measure current loudness levels
2. Normalize using measured values for accurate results
3. Output with suffix `_normalized` in same format (or user-specified format)
4. Display before/after summary

## Step 1: Analyze Audio

Run the analysis pass to measure loudness:

```bash
ffmpeg -i "<input-file>" -af "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=summary" -f null -
```

Parse the output for these values:
- `Input Integrated` → measured_I (e.g., -22.6)
- `Input True Peak` → measured_TP (e.g., -2.6)
- `Input LRA` → measured_LRA (e.g., 19.8)
- `Input Threshold` → measured_thresh (e.g., -35.1)

## Step 2: Normalize Audio

Run the normalization pass with measured values. Choose encoder based on output format:

| Format | Encoder flags |
|--------|---------------|
| mp3    | `-c:a libmp3lame -q:a 2` |
| m4a    | `-c:a aac -b:a 192k` |
| flac   | `-c:a flac` |
| wav    | `-c:a pcm_s16le` |
| ogg    | `-c:a libvorbis -q:a 6` |

```bash
ffmpeg -i "<input-file>" -af "loudnorm=I=-16:LRA=11:TP=-1.5:measured_I=<measured_I>:measured_LRA=<measured_LRA>:measured_TP=<measured_TP>:measured_thresh=<measured_thresh>" <encoder-flags> "<output-file>"
```

Output file: Same directory, base name with `_normalized` suffix, same extension as input (e.g., `audio.m4a` → `audio_normalized.m4a`).

## Step 3: Display Summary

Present a before/after comparison:

```
## Audio Normalization Summary

| Metric           | Before     | Target     |
|------------------|------------|------------|
| Integrated       | -22.6 LUFS | -16.0 LUFS |
| True Peak        | -2.6 dBTP  | -1.5 dBTP  |
| Loudness Range   | 19.8 LU    | 11.0 LU    |

Output: /path/to/audio_normalized.m4a
```

## Target Levels

Default targets optimized for podcasts/YouTube/general streaming:

- **Integrated loudness**: -16 LUFS
- **True peak**: -1.5 dBTP (headroom for lossy encoding)
- **Loudness range**: 11 LU

Other platform standards for reference: Spotify/YouTube (-14 LUFS), broadcast EBU R128 (-23 LUFS).
