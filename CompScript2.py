from pyaudio import paInt16, PyAudio, paContinue
from numpy import exp,iinfo,int16,clip,zeros_like,abs,frombuffer
from wave import open
from tkinter import *
from os import system

# Default compressor settings
threshold=-20                               # Level compressor algorithm activates in dB
ratio=4                                     # Compression ratio
attack_time=0.01                            # Attack time in seconds (0.01=10 ms, default)
release_time=0.1                            # Release time in seconds (0.1=100 ms, default)
buffer_size=4096                            # Buffer time, change to counter possible clicking/distortion
sample_format=paInt16                       # Bit rate compressor runs at (16 bit)
channels=1                                  # Amount of audio channels the compressor works with
fs=44100                                    # Sample rate  compressor runs at (44.1 kHz)
wav_output_filename="outputCompScript.wav"  # WAV file name, used to prove compressor is working

p = PyAudio() # Initializing pyaudio

def find_device_index(device_name):
    for i in range(p.get_device_count()):
        device_info=p.get_device_info_by_index(i)
        print(f"Device {i}: {device_info['name']}")
        if device_name in device_info.get('name'):
            return i
    return None

def calculate_coefficient(time,sample_rate):
    return exp(-1.0/(time*sample_rate))

def apply_gain(sample,gain):
    processed_sample=int16(gain*sample)
    max_amplitude=iinfo(int16).max
    return clip(processed_sample,-max_amplitude,max_amplitude)

def compressor(audio_data,threshold_db,ratio,attack,release,sample_rate,knee_width):
    threshold=int16(10**(threshold_db / 20))
    knee_start=threshold-knee_width/2
    compressed_data=zeros_like(audio_data)
    gain=1
    previous_gain=1
    for i, sample in enumerate(audio_data):
        sample_abs=abs(sample)
        if sample_abs>knee_start:
            if sample_abs>threshold:
                excess=sample_abs-threshold
                compressed_level=excess/ratio+threshold
                target_gain=compressed_level/sample_abs
            else:
                knee_factor=(sample_abs-knee_start)/knee_width
                target_gain=1-knee_factor*(1-1/ratio)
        else:
            target_gain=1
        attack_coeff=calculate_coefficient(attack,sample_rate)
        release_coeff=calculate_coefficient(release,sample_rate)
        if target_gain<previous_gain:
            gain=target_gain+(previous_gain-target_gain)*attack_coeff
        else:
            gain=target_gain+(previous_gain-target_gain)*release_coeff
        compressed_data[i]=apply_gain(sample,gain)
        previous_gain=gain
    return compressed_data

class CompressorGUI:
    def __init__(self,master):
        self.master=master
        master.title("Audio Compressor")
        self.threshold_scale=Scale(master,from_=-60,to=0,orient='horizontal',label='Threshold (dB)')
        self.threshold_scale.set(-20)
        self.threshold_scale.pack(fill='x',expand=True)
        self.ratio_scale=Scale(master,from_=1,to=20,orient='horizontal',label='Ratio')
        self.ratio_scale.set(4)
        self.ratio_scale.pack(fill='x',expand=True)
        self.attack_scale=Scale(master,from_=0.01,to=1,resolution=0.01,orient='horizontal',label='Attack (s)')
        self.attack_scale.set(0.01)
        self.attack_scale.pack(fill='x',expand=True)
        self.release_scale=Scale(master,from_=0.01,to=1,resolution=0.01,orient='horizontal',label='Release (s)')
        self.release_scale.set(0.1)
        self.release_scale.pack(fill='x',expand=True)
        self.stop_button=Button(master,text="Stop and Restart",command=self.stop_and_restart)
        self.stop_button.pack()

    def stop_and_restart(self):
        global stream,wf,p
        stream.stop_stream()
        stream.close()
        wf.close()
        p.terminate()
        print("Stream stopped and WAV file saved")
        self.master.destroy()
        system('sudo reboot')
        
input_device_index=find_device_index("M4: USB Audio")     # WILL ONLY WORK WITH MOTU M4
output_device_index=find_device_index("M4: USB Audio")    # WILL ONLY WORK WITH MOTU M4
current_gain=1.0
wf=open(wav_output_filename,'wb')   # Starting the WAV file recording
wf.setnchannels(channels)
wf.setsampwidth(p.get_sample_size(sample_format))
wf.setframerate(fs)
knee_width_db=5

def callback(in_data,frame_count,time_info,status):
    global app
    audio_data=frombuffer(in_data,dtype=int16)
    compressed_data=compressor(
        audio_data, 
        app.threshold_scale.get(), 
        app.ratio_scale.get(), 
        app.attack_scale.get(), 
        app.release_scale.get(), 
        fs,
        knee_width_db
    )
    wf.writeframes(compressed_data.tobytes())
    return (compressed_data.tobytes(),paContinue)

root=Tk()
root.wm_attributes('-zoomed',True)
app=CompressorGUI(root)
stream=p.open(format=sample_format,
                channels=channels,
                rate=fs,
                input=True,
                output=True,
                frames_per_buffer=buffer_size,
                input_device_index=input_device_index,
                output_device_index=output_device_index,
                stream_callback=callback)
stream.start_stream()
root.mainloop()