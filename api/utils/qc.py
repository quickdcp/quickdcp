# Minimal QC stubs.
# Replace these with real video/audio/subtitle analysis pipelines.

def qc_video_stub() -> dict:
    return {
        "black_frames": 0,
        "flicker": 0,
        "bad_frames": 0
    }


def qc_audio_stub() -> dict:
    return {
        "lufs": -23.0,
        "silence_segments": 0,
        "phase_invert": False
    }


def qc_subs_stub() -> dict:
    return {
        "sync_ms": 10,
        "encoding": "UTF-8",
        "warnings": []
    }
