import os
import json
import numpy as np
import scipy.io.wavfile as wav
from moviepy import VideoFileClip

# 256 optimally spaced synthesis bands focused on the core audio spectrum
TARGET_FREQS = np.logspace(np.log10(40), np.log10(3500), num=256, dtype=int).tolist()

def bake_audio(video_path):
    video_name = os.path.splitext(video_path)[0]
    temp_wav = f"{video_name}_temp.wav"
    
    print(f"🎬 Loading video details for {video_path}...")
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            print(f"❌ No audio track found in {video_path}")
            return
            
        native_fps = video.fps
        print(f"⚡ Detected original video speed: {native_fps} FPS")
        
        print(f"🎵 Extracting raw audio track...")
        video.audio.write_audiofile(temp_wav, fps=44100, nbytes=2, codec='pcm_s16le', logger=None)
        video.close()
    except Exception as e:
        print(f"❌ Failed to parse video metadata or extract audio: {e}")
        return

    sample_rate, data = wav.read(temp_wav)
    if len(data.shape) > 1:
        data = data.mean(axis=1)
        
    max_val = np.max(np.abs(data))
    if max_val > 0:
        data = data / max_val
    
    samples_per_frame = int(sample_rate / native_fps)
    total_frames = int(len(data) / samples_per_frame)
    
    audio_track_data = []
    
    # Pre-calculate a Hanning window to prevent spectral leakage (hardware emulation style)
    window = np.hanning(samples_per_frame)
    
    print(f"📊 Baking hardware-optimized matrix for {len(TARGET_FREQS)} channels...")
    
    for f in range(total_frames):
        start_idx = f * samples_per_frame
        end_idx = start_idx + samples_per_frame
        frame_chunk = data[start_idx:end_idx]
        
        if len(frame_chunk) < samples_per_frame:
            break
            
        # Apply windowing function to sharpen frequency boundaries
        windowed_chunk = frame_chunk * window
        
        fft_data = np.abs(np.fft.rfft(windowed_chunk))
        fft_freqs = np.fft.rfftfreq(len(windowed_chunk), d=1.0/sample_rate)
        
        frame_amplitudes = {}
        
        for target in TARGET_FREQS:
            idx = (np.abs(fft_freqs - target)).argmin()
            
            # Convert to sharp decibel scale
            raw_val = fft_data[idx] / (samples_per_frame / 2)
            log_volume = 20 * np.log10(raw_val + 1e-5)
            
            # Dynamic range compression (curves the sound to match hardware chips)
            normalized_vol = np.clip((log_volume + 50) / 50, 0.0, 1.0)
            
            # Subtle low-frequency emphasis curve
            equalized_vol = normalized_vol * (1.1 - (target / 4000.0))
            
            frame_amplitudes[f"{target}Hz"] = round(float(np.clip(equalized_vol, 0.0, 1.0)), 4)
            
        audio_track_data.append(frame_amplitudes)
        
    output_filename = f"{video_name}_audio.json"
    with open(output_filename, "w") as json_file:
        json.dump(audio_track_data, json_file)
        
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
        
    print(f"💾 Chip-tuned matrix saved to: {output_filename}\n")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video_sync = file
        bake_audio(file)
