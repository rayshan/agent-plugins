---
name: audio-normalize
description: This skill should be used when the user asks to "normalize audio", "prepare audio for transcription", "preprocess audio for speech recognition", "clean audio for transcription", "fix audio volume", "make audio louder", or provides an audio file for volume normalization or transcription preparation. Uses ffmpeg for audio preprocessing and two-pass loudnorm normalization.
argument-hint: [audio-file-path]
---

Preprocess and normalize audio for optimal speech transcription accuracy using ffmpeg. Apply this five-stage pipeline to clean, normalize, and resample audio into a format optimized for transcription models.

## Pipeline

1. **Mono downmix** — Combine stereo to mono (transcription models expect mono)
2. **High-pass filter (80 Hz)** — Remove low-frequency rumble carrying no speech information
3. **Noise reduction (`afftdn`)** — Reduce stationary background noise (room tone, HVAC)
4. **Loudnorm (two-pass)** — Normalize to consistent loudness level (-16 LUFS)
5. **Resample to 16 kHz WAV** — Match transcription model expectations (Whisper, etc.)

## Target Levels

Default targets optimized for speech transcription:

- **Integrated loudness**: -16 LUFS
- **True peak**: -1.5 dBTP
- **Loudness range**: 11 LU

## Step 1: Analyze Audio

Run the analysis pass through the full filter chain to measure post-processed loudness:

```bash
ffmpeg -i "<input-file>" -af "pan=mono|c0=0.5*c0+0.5*c1,highpass=f=80,afftdn=nf=-25,loudnorm=I=-16:LRA=11:TP=-1.5:print_format=summary" -f null -
```

Parse the output for these values:
- `Input Integrated` → measured_I
- `Input True Peak` → measured_TP
- `Input LRA` → measured_LRA
- `Input Threshold` → measured_thresh

## Step 2: Process and Normalize

Run the full pipeline with measured loudnorm values:

```bash
ffmpeg -i "<input-file>" -af "pan=mono|c0=0.5*c0+0.5*c1,highpass=f=80,afftdn=nf=-25,loudnorm=I=-16:LRA=11:TP=-1.5:measured_I=<measured_I>:measured_LRA=<measured_LRA>:measured_TP=<measured_TP>:measured_thresh=<measured_thresh>" -ar 16000 -c:a pcm_s16le "<output-file>"
```

Output file: Same directory, base name with `_transcription` suffix, `.wav` extension (e.g., `meeting.m4a` → `meeting_transcription.wav`).

## Step 3: Display Summary

Present a before/after comparison:

```
## Audio Processing Summary

| Step             | Detail                    |
|------------------|---------------------------|
| Mono downmix     | Stereo → Mono             |
| High-pass filter | 80 Hz cutoff              |
| Noise reduction  | afftdn (nf=-25)           |
| Loudnorm         | <measured_I> → -16.0 LUFS |
| Resample         | <original_rate> → 16 kHz  |
| Format           | PCM 16-bit WAV            |

Output: /path/to/audio_transcription.wav
```

## Filter Details

- **`pan=mono|c0=0.5*c0+0.5*c1`** — Equal mix of left and right channels
- **`highpass=f=80`** — Butterworth high-pass, removes sub-80 Hz rumble
- **`afftdn=nf=-25`** — FFT-based denoiser for stationary noise (HVAC, room tone); works best in quiet recording environments
- **`loudnorm`** — EBU R128 loudness normalization, two-pass for accuracy
