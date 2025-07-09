# Contemplative AI - Audio Player

A simple web-based audio player for the `voz_kokoro.wav` file.

## Features

- 🎵 Play/pause audio controls
- ⏱️ Display audio duration
- ⌨️ Keyboard shortcuts:
  - **Space**: Play/pause
  - **Left Arrow**: Skip 10 seconds backward
  - **Right Arrow**: Skip 10 seconds forward
- 📱 Responsive design for mobile devices
- 🎨 Modern, beautiful UI with gradient background

## How to Use

1. Open `index.html` in your web browser
2. Click the play button to start listening to the audio
3. Use the audio controls to adjust volume, seek, or pause
4. Use keyboard shortcuts for quick control

## File Structure

```
web-ui/
├── index.html      # Main HTML file
├── styles.css      # CSS styling
├── script.js       # JavaScript functionality
└── README.md       # This file
```

## Audio File

The player is configured to play the file located at `../data/audio/voz_kokoro.wav` relative to the web-ui directory.

## Browser Compatibility

This player works in all modern browsers that support the HTML5 `<audio>` element:
- Chrome
- Firefox
- Safari
- Edge

## Development

To modify the player:
- Edit `styles.css` for visual changes
- Edit `script.js` for functionality changes
- Edit `index.html` for structure changes

No build process or dependencies required - just open the HTML file in a browser! 