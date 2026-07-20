import os
import json
import numpy as np
import scipy.io.wavfile as wav
from moviepy.editor import VideoFileClip

# The 7 target frequencies we are monitoring
TARGET_FREQS = [60, 100, 500, 1000, 3000, 6000, 10000]

def bake_audio(video_path):
    video_name = os.path.splitext(video_path)[0]
    temp_wav = f"{video_name}_temp.wav"
    
    print(f"🎬 Loading video details for {video_path}...")
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            print(f"❌ No audio track found in {video_path}")
            return
            
        # Dynamically acquire the native frame rate of the original MP4 file
        native_fps = video.fps
        print(f"⚡ Detected original video speed: {native_fps} FPS")
        
        print(f"🎵 Extracting raw audio track...")
        video.audio.write_audiofile(temp_wav, fps=44100, nbytes=2, codec='pcm_s16le', logger=None)
        video.close()
    except Exception as e:
        print(f"❌ Failed to parse video metadata or extract audio: {e}")
        return

    # Load the extracted audio file
    sample_rate, data = wav.read(temp_wav)
    
    # Mix to mono if it's stereo
    if len(data.shape) > 1:
        data = data.mean(axis=1)
        
    # Normalize data between -1.0 and 1.0
    max_val = np.max(np.abs(data))
    if max_val > 0:
        data = data / max_val
    
    # Calculate how many audio samples belong to exactly one video frame based on original FPS
    samples_per_frame = int(sample_rate / native_fps)
    total_frames = int(len(data) / samples_per_frame)
    
    audio_track_data = []
    
    print(f"📊 Analyzing frequency bands across {total_frames} matching frames...")
    
    for f in range(total_frames):
        start_idx = f * samples_per_frame
        end_idx = start_idx + samples_per_frame
        frame_chunk = data[start_idx:end_idx]
        
        if len(frame_chunk) == 0:
            break
            
        # Run standard FFT analysis
        fft_data = np.abs(np.fft.rfft(frame_chunk))
        fft_freqs = np.fft.rfftfreq(len(frame_chunk), d=1.0/sample_rate)
        
        frame_amplitudes = {}
        
        # Find the volume level for each target frequency
        for target in TARGET_FREQS:
            # Find the closest frequency match in our FFT data array
            idx = (np.abs(fft_freqs - target)).argmin()
            # Calculate raw volume scale and clamp it safely between 0.0 and 1.0
            volume = float(np.clip(fft_data[idx] / (samples_per_frame / 2), 0.0, 1.0))
            frame_amplitudes[f"{target}Hz"] = round(volume, 4)
            
        audio_track_data.append(frame_amplitudes)
        
    # Save the output to a master JSON file
    output_filename = f"{video_name}_audio.json"
    with open(output_filename, "w") as json_file:
        json.dump(audio_track_data, json_file)
        
    # Clean up temporary audio file
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
        
    print(f"💾 Successfully baked audio data! Saved to: {output_filename}\n")

# Process all MP4 files in the directory
for file in os.listdir('.'):
    if file.endswith('.mp4'):
        bake_audio(file)
