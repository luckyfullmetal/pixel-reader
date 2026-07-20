import os
import json
import numpy as np
import scipy.io.wavfile as wav
from moviepy import VideoFileClip

# 8192 raw high-density channels mapped across the audible frequency range
TARGET_FREQS = np.logspace(np.log10(20), np.log10(4500), num=8192, dtype=int).tolist()

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
        print(f"❌ Failed to parse video: {e}")
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
    
    print(f"📊 Slicing RAW 8192-band acoustic spectrum matrix...")
    
    for f in range(total_frames):
        start_idx = f * samples_per_frame
        end_idx = start_idx + samples_per_frame
        frame_chunk = data[start_idx:end_idx]
        
        if len(frame_chunk) < samples_per_frame:
            break
            
        # Pure unwindowed Fast Fourier Transform
        fft_data = np.abs(np.fft.rfft(frame_chunk))
        fft_freqs = np.fft.rfftfreq(len(frame_chunk), d=1.0/sample_rate)
        
        frame_amplitudes = {}
        
        for target in TARGET_FREQS:
            idx = (np.abs(fft_freqs - target)).argmin()
            raw_val = fft_data[idx] / (samples_per_frame / 2)
            
            # Direct 1:1 raw float assignment bounded between 0.0 and 1.0
            frame_amplitudes[f"{target}Hz"] = round(float(np.clip(raw_val, 0.0, 1.0)), 4)
            
        audio_track_data.append(frame_amplitudes)
        
    output_filename = f"{video_name}_audio.json"
    with open(output_filename, "w") as json_file:
        json.dump(audio_track_data, json_file)
        
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
        
    print(f"💾 Raw extreme mega-matrix saved to: {output_filename}\n")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        bake_audio(file)
