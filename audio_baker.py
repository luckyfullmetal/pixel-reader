import os
import json
import numpy as np
import scipy.io.wavfile as wav
from moviepy import VideoFileClip

NUM_CHANNELS = 256

# Functions to convert back and forth between Hz and Mel scale
def hz_to_mel(hz):
    return 2595 * np.log10(1 + hz / 700.0)

def mel_to_hz(mel):
    return 700 * (10**(mel / 2595.0) - 1)

def bake_audio(video_path):
    video_name = os.path.splitext(video_path)[0]
    temp_wav = f"{video_name}_temp.wav"
    
    print(f"🎬 Loading video details for {video_path}...")
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            return
        native_fps = video.fps
        video.audio.write_audiofile(temp_wav, fps=44100, nbytes=2, codec='pcm_s16le', logger=None)
        video.close()
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return

    sample_rate, data = wav.read(temp_wav)
    if len(data.shape) > 1:
        data = data.mean(axis=1)
        
    max_val = np.max(np.abs(data))
    if max_val > 0:
        data = data / max_val
    
    samples_per_frame = int(sample_rate / native_fps)
    total_frames = int(len(data) / samples_per_frame)
    fft_size = samples_per_frame
    
    # 1. Generate Mel-spaced center frequencies
    min_mel = hz_to_mel(40)
    max_mel = hz_to_mel(5000) # Capped at 5kHz where the human ear does the most work
    mel_points = np.linspace(min_mel, max_mel, NUM_CHANNELS + 2)
    hz_points = mel_to_hz(mel_points)
    
    # Map Hz points to FFT bin indices
    bins = np.floor((fft_size + 1) * hz_points / sample_rate).astype(int)
    
    # 2. Construct Triangular Mel-Filter Banks
    filters = np.zeros((NUM_CHANNELS, int(fft_size / 2 + 1)))
    for m in range(1, NUM_CHANNELS + 1):
        for k in range(bins[m - 1], bins[m]):
            filters[m - 1, k] = (k - bins[m - 1]) / (bins[m] - bins[m - 1])
        for k in range(bins[m], bins[m + 1]):
            filters[m - 1, k] = (bins[m + 1] - k) / (bins[m + 1] - bins[m])

    # Round center frequencies to label our audio channels cleanly
    center_hz_channels = [int(hz_points[m]) for m in range(1, NUM_CHANNELS + 1)]
    
    audio_track_data = []
    window = np.hanning(samples_per_frame)
    
    print(f"🧠 Baking Human-Hearing Optimized Mel Matrix ({NUM_CHANNELS} channels)...")
    
    for f in range(total_frames):
        start_idx = f * samples_per_frame
        end_idx = start_idx + samples_per_frame
        frame_chunk = data[start_idx:end_idx]
        
        if len(frame_chunk) < samples_per_frame:
            break
            
        # Run windowed power spectrum analysis
        fft_power = np.abs(np.fft.rfft(frame_chunk * window)) ** 2
        
        # Apply the Mel filter banks to group raw frequencies into human-perceived bands
        mel_energies = np.dot(filters, fft_power)
        
        frame_amplitudes = {}
        for i, center_hz in enumerate(center_hz_channels):
            # Dynamic range compression (Logarithmic Decibel curve mapping)
            log_energy = 10 * np.log10(mel_energies[i] + 1e-8)
            normalized_vol = np.clip((log_energy + 45) / 45, 0.0, 1.0)
            
            frame_amplitudes[f"{center_hz}Hz"] = round(float(normalized_vol), 4)
            
        audio_track_data.append(frame_amplitudes)
        
    output_filename = f"{video_name}_audio.json"
    with open(output_filename, "w") as json_file:
        json.dump(audio_track_data, json_file)
        
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
    print(f"💾 Mel-Scale tuned matrix saved to: {output_filename}\n")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        bake_audio(file)
