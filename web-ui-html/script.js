document.addEventListener('DOMContentLoaded', function() {
    const audioPlayer = document.getElementById('audioPlayer');
    const durationSpan = document.getElementById('duration');
    
    // Function to format time in MM:SS format
    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
    // Update duration when metadata is loaded
    audioPlayer.addEventListener('loadedmetadata', function() {
        const duration = audioPlayer.duration;
        if (duration && !isNaN(duration)) {
            durationSpan.textContent = `Duration: ${formatTime(duration)}`;
        } else {
            durationSpan.textContent = 'Duration: Unknown';
        }
    });
    
    // Handle audio loading errors
    audioPlayer.addEventListener('error', function() {
        durationSpan.textContent = 'Error: Could not load audio file';
        console.error('Audio loading error:', audioPlayer.error);
    });
    
    // Add some interactive features
    audioPlayer.addEventListener('play', function() {
        console.log('Audio started playing');
    });
    
    audioPlayer.addEventListener('pause', function() {
        console.log('Audio paused');
    });
    
    audioPlayer.addEventListener('ended', function() {
        console.log('Audio finished playing');
    });
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        switch(event.code) {
            case 'Space':
                event.preventDefault();
                if (audioPlayer.paused) {
                    audioPlayer.play();
                } else {
                    audioPlayer.pause();
                }
                break;
            case 'ArrowRight':
                event.preventDefault();
                audioPlayer.currentTime += 10; // Skip 10 seconds forward
                break;
            case 'ArrowLeft':
                event.preventDefault();
                audioPlayer.currentTime -= 10; // Skip 10 seconds backward
                break;
        }
    });
    
    // Add a visual indicator when audio is loading
    audioPlayer.addEventListener('loadstart', function() {
        durationSpan.classList.add('loading');
    });
    
    audioPlayer.addEventListener('canplay', function() {
        durationSpan.classList.remove('loading');
    });
}); 