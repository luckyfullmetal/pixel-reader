import os
import base64
import struct
import numpy as np
import scipy.io.wavfile as wav
from moviepy import VideoFileClip

# 2048 channels distributed logarithmically across the human acoustic spectrum
ALL_FREQS = np.logspace(np.log10(20), np.log10(4000), num=2048, dtype=int).tolist()

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
    
    # Structural Binary packing initialization
    # We will use 1 single byte (0-255) per frequency to keep it extraordinarily tiny
    binary_payload = bytearray()
    
    print(f"📊 Slicing RAW 3-Zone 2048-band into compressed binary stream...")
    
    for f in range(total_frames):
        start_idx = f * samples_per_frame
        end_idx = start_idx + samples_per_frame
        frame_chunk = data[start_idx:end_idx]
        
        if len(frame_chunk) < samples_per_frame:
            break
            
        fft_data = np.abs(np.fft.rfft(frame_chunk))
        fft_freqs = np.fft.rfftfreq(len(frame_chunk), d=1.0/sample_rate)
        
        for target in ALL_FREQS:
            idx = (np.abs(fft_freqs - target)).argmin()
            raw_val = fft_data[idx] / (samples_per_frame / 2)
            clamped_val = np.clip(raw_val, 0.0, 1.0)
            
            # Convert 0.0-1.0 float directly to a single 8-bit unsigned integer byte (0-255)
            byte_val = int(clamped_val * 255)
            binary_payload.append(byte_val)
            
    # Encode the binary payload to a clean string format safe for HTTP transport
    b64_string = base64.b64encode(binary_payload).decode('utf-8')
    
    output_filename = f"{video_name}_audio.txt"
    with open(output_filename, "w") as out_file:
        out_file.write(b64_string)
        
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
        
    print(f"💾 Ultra-compressed binary stream saved to: {output_filename}")
    print(f"📉 Size reduction achieved! File size is now minimal.\n")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        bake_audio(file)
