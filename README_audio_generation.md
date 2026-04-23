# Audio Generation Script for Meditation Content

## Overview
This script processes meditation JSON files from Cloudflare R2 and generates complete audio files with proper silence intervals.

## Key Features

### 1. Content Parsing
- Parses meditation content line by line
- Identifies instructions vs silence intervals
- Handles format: `[silencio: X segundos]`

### 2. Audio Generation
- Generates individual TTS audio for each instruction
- Creates silence segments for specified durations
- Uses Qwen3-TTS model with customizable voice

### 3. Audio Processing
- Combines all segments into one final audio file
- Handles sample rate conversion between segments
- Maintains proper timing and synchronization

### 4. File Management
- Saves individual segments to R2 storage
- Saves combined audio to R2 storage
- Creates local backup files for debugging

## Workflow

1. **Connect to R2**: Prompts for credentials and connects to Cloudflare R2
2. **Select JSON**: Lists and selects most recent meditation JSON file
3. **Parse Content**: Extracts instructions and silence intervals
4. **Generate Audio**: Creates TTS for instructions, silence for pauses
5. **Combine Audio**: Stitches all segments together
6. **Save Files**: Uploads both individual segments and combined audio

## Output Structure

### Individual Segments
- `segment_001_instruction.wav` - First instruction
- `segment_002_silence_15s.wav` - 15-second silence
- `segment_003_instruction.wav` - Second instruction
- etc.

### Combined Audio
- `{json_id}_full_audio.wav` - Complete meditation audio

## Usage in Jupyter

The script is organized in cells for Jupyter notebook execution:

- **Cell 1**: Install dependencies and load model
- **Cell 2**: Main processing workflow

## Voice Configuration

Default voice settings:
- Soft, female voice
- Mid-range, very slow pace
- Argentinian accent
- Warm, breathy resonance
- Deliberate spacing between words

Can be customized by modifying the `VOICE_DESC` variable.

## Error Handling

- Handles R2 connection errors
- Validates JSON content structure
- Provides fallback default meditation text
- Reports processing progress and completion status
