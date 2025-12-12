import modal
import logging
from pathlib import Path

# ---------------------------------------------------------
# Application config
# ---------------------------------------------------------
config = {
    # General
    'app_name': 'transcription',

    # Front-End (FastAPI)
    'api': {
        'cpu': 1,
        'memory': 1024,
        'min_containers': 0,
        'max_containers': 2,
        'scaledown_window': 60,
        'timeout': 300,
        'concurrency': 5,
    },

    # Back-End (Faster Whisper)
    'whisper': {
        'cpu': 2,
        'memory': 1024,
        'min_containers': 0,
        'max_containers': 5,
        'scaledown_window': 60,
        'timeout': 300,
        'concurrency': 1,
        'model': {
            'model_size': 'small',
            'beam_size': 1,
            'source_language': 'en',
            'device': 'cpu',
            'compute_type': 'int8',
        }
    },

    # Supported formats
    'supported_audio_formats': ['mp3', 'm4a', 'wav', 'flac', 'aac', 'ogg'],
    'supported_video_formats': ['mp4', 'mov', 'avi', 'mkv', 'webm'],
}

# ---------------------------------------------------------
# Modal image
# ---------------------------------------------------------
local_root = Path(__file__).resolve().parent
image = (
    modal.Image.debian_slim()
    .apt_install("ffmpeg")
    .uv_sync()
    .add_local_dir(
        local_root,
        remote_path="/app",
        ignore=[".venv"]
    )
)

# ---------------------------------------------------------
# Logger setup
# ---------------------------------------------------------
logger = logging.getLogger("transcription")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()  # Log to console only
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
