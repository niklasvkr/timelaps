import sys
import threading
from ids_peak import ids_peak as peak
import numpy as np
from ids_peak_ipl import ids_peak_ipl
import time
import cv2
import threading
import os
from PIL import Image, ImageChops
from functools import reduce
import configparser
import json
from datetime import datetime

peak.Library.Initialize()

class IDSCamera():

    def __init__(self):
    
        self.device = None
        self.data_stream = None
        self.node_map_remote_device = None
        self.pipeline_source = None
        self.live = False

    def open_camera(self, index):
        try:
            # Create instance of the device manager
            device_manager = peak.DeviceManager.Instance()
            
            # Update the device manager
            device_manager.Update()
            
            # Return if no device was found
            if device_manager.Devices().empty():
                return False
            
            # open the first openable device in the device manager's device list
            device_count = device_manager.Devices().size()
            print("IDS cameras: ", device_count)
            if device_manager.Devices()[index].IsOpenable():
                self.device = device_manager.Devices()[index].OpenDevice(peak.DeviceAccessType_Control)
            
                # Get NodeMap of the RemoteDevice for all accesses to the GenICam NodeMap tree
                self.node_map_remote_device = self.device.RemoteDevice().NodeMaps()[0]
            
                return True
        except Exception as e:
            print(e)
     
        return False
     
     
    def prepare_acquisition(self):
        try:
            data_streams = self.device.DataStreams()
            if data_streams.empty():
                # no data streams available
                return False
        
            self.data_stream = self.device.DataStreams()[0].OpenDataStream()
        
            return True
        except Exception as e:
            print(e)
        
        return False
     
     
    def set_roi(self, x, y, width, height):
        try:
            # Get the minimum ROI and set it. After that there are no size restrictions anymore
            x_min = self.node_map_remote_device.FindNode("OffsetX").Minimum()
            y_min = self.node_map_remote_device.FindNode("OffsetY").Minimum()
            w_min = self.node_map_remote_device.FindNode("Width").Minimum()
            h_min = self.node_map_remote_device.FindNode("Height").Minimum()
            
            self.node_map_remote_device.FindNode("OffsetX").SetValue(x_min)
            self.node_map_remote_device.FindNode("OffsetY").SetValue(y_min)
            self.node_map_remote_device.FindNode("Width").SetValue(w_min)
            self.node_map_remote_device.FindNode("Height").SetValue(h_min)
            
            # Get the maximum ROI values
            x_max = self.node_map_remote_device.FindNode("OffsetX").Maximum()
            y_max = self.node_map_remote_device.FindNode("OffsetY").Maximum()
            w_max = self.node_map_remote_device.FindNode("Width").Maximum()
            h_max = self.node_map_remote_device.FindNode("Height").Maximum()
     
            if (x < x_min) or (y < y_min) or (x > x_max) or (y > y_max):
                return False
            elif (width < w_min) or (height < h_min) or ((x + width) > w_max) or ((y + height) > h_max):
                return False
            else:
                # Now, set final AOI
                self.node_map_remote_device.FindNode("OffsetX").SetValue(x)
                self.node_map_remote_device.FindNode("OffsetY").SetValue(y)
                self.node_map_remote_device.FindNode("Width").SetValue(width)
                self.node_map_remote_device.FindNode("Height").SetValue(height)
            
            return True
        except Exception as e:
            print(e)
     
        return False

    def get_red_gain(self):
        self.node_map_remote_device.FindNode("GainSelector").SetCurrentEntry("DigitalRed")
        return self.node_map_remote_device.FindNode("Gain").Value()
         
    def set_red_gain(self, value):
        self.node_map_remote_device.FindNode("GainSelector").SetCurrentEntry("DigitalRed")
        self.node_map_remote_device.FindNode("Gain").SetValue(value)

    def get_green_gain(self):
        self.node_map_remote_device.FindNode("GainSelector").SetCurrentEntry("DigitalGreen")
        return self.node_map_remote_device.FindNode("Gain").Value()
         
    def set_green_gain(self, value):
        self.node_map_remote_device.FindNode("GainSelector").SetCurrentEntry("DigitalGreen")
        self.node_map_remote_device.FindNode("Gain").SetValue(value)


    def get_blue_gain(self):
        self.node_map_remote_device.FindNode("GainSelector").SetCurrentEntry("DigitalBlue")
        return self.node_map_remote_device.FindNode("Gain").Value()
         
    def set_blue_gain(self, value):
        self.node_map_remote_device.FindNode("GainSelector").SetCurrentEntry("DigitalBlue")
        self.node_map_remote_device.FindNode("Gain").SetValue(value)


    
    def get_min_max_red_gain(self):
        self.node_map_remote_device.FindNode("GainSelector").SetCurrentEntry("DigitalRed")
        min = self.node_map_remote_device.FindNode("Gain").Minimum()
        max = self.node_map_remote_device.FindNode("Gain").Maximum()
        return min, max
        
    def get_min_max_green_gain(self):
        self.node_map_remote_device.FindNode("GainSelector").SetCurrentEntry("DigitalGreen")
        min = self.node_map_remote_device.FindNode("Gain").Minimum()
        max = self.node_map_remote_device.FindNode("Gain").Maximum()
        return min, max

    def get_min_max_blue_gain(self):
        self.node_map_remote_device.FindNode("GainSelector").SetCurrentEntry("DigitalBlue")
        min = self.node_map_remote_device.FindNode("Gain").Minimum()
        max = self.node_map_remote_device.FindNode("Gain").Maximum()
        return min, max
        
    def set_exposure(self, value):
        self.node_map_remote_device.FindNode("ExposureTime").SetValue(value)
        
    def get_exposure(self):
        return self.node_map_remote_device.FindNode("ExposureTime").Value()
        
    def get_min_max_exposure(self):
        min = self.node_map_remote_device.FindNode("ExposureTime").Minimum()
        max = self.node_map_remote_device.FindNode("ExposureTime").Maximum()
        return min, max

    def alloc_and_announce_buffers(self):
        try:
            if self.data_stream:
                # Flush queue and prepare all buffers for revoking
                self.data_stream.Flush(peak.DataStreamFlushMode_DiscardAll)
            
            # Clear all old buffers
            for buffer in self.data_stream.AnnouncedBuffers():
                self.data_stream.RevokeBuffer(buffer)
            
            payload_size = self.node_map_remote_device.FindNode("PayloadSize").Value()
            
            # Get number of minimum required buffers
            num_buffers_min_required = self.data_stream.NumBuffersAnnouncedMinRequired()
            
            # Alloc buffers
            for count in range(num_buffers_min_required):
                buffer = self.data_stream.AllocAndAnnounceBuffer(payload_size)
                self.data_stream.QueueBuffer(buffer)
            
            return True
        except Exception as e:
            print(e)
        
        return False
     
 
    
    def start_acquisition(self):
        try:
            
            print("starting acq")
            self.alloc_and_announce_buffers()
            self.data_stream.StartAcquisition(peak.AcquisitionStartMode_Default, peak.DataStream.INFINITE_NUMBER)
            self.node_map_remote_device.FindNode("TLParamsLocked").SetValue(1)
            self.node_map_remote_device.FindNode("AcquisitionStart").Execute()
            self.live = True

      

            return True
        except Exception as e:
            print(e)
     
        return False
    

    def stop_acquisition(self):
        self.live = False
        self.node_map_remote_device.FindNode("AcquisitionStop").Execute()
        self.node_map_remote_device.FindNode("TLParamsLocked").SetValue(0)
        self.data_stream.StopAcquisition(peak.AcquisitionStopMode_Default)
        print("acq ended!")

        
    def get_frame(self):
        try:
            # Get buffer from device's DataStream. Wait 5000 ms. The buffer is automatically locked until it is queued again.
            buffer = self.data_stream.WaitForFinishedBuffer(5000)
            
            image = ids_peak_ipl.Image.CreateFromSizeAndBuffer(
                buffer.PixelFormat(),
                buffer.BasePtr(),
                buffer.Size(),
                buffer.Width(),
                buffer.Height()
            )
            image = image.ConvertTo(ids_peak_ipl.PixelFormatName_RGB8, ids_peak_ipl.ConversionMode_Fast)
            self.data_stream.QueueBuffer(buffer)

            return image
        
        except Exception as e:
            print(e)
            return None
            return np.random.randint(low=0,high=255,size=(480,640,3),dtype=np.uint8)
    
    def capture_and_show(self):
        while self.live:
            frame = self.get_frame()
            if frame is not None:
                buffer = frame.Buffer()
                frame_np = np.frombuffer(buffer, dtype=np.uint8).reshape((frame.Height(), frame.Width(), 3))
                frame_rgb = cv2.cvtColor(frame_np, cv2.COLOR_BGR2RGB)
                cv2.imshow('Live Video', frame_rgb)
                cv2.waitKey(1)  # Warte 1 Millisekunde, um das Fenster zu aktualisieren
        cv2.destroyAllWindows()




    def start_live_view(self):
        try:
            print("Starting live view")
            self.live = True
            self.capture_thread = threading.Thread(target=self.capture_and_show)
            self.capture_thread.start()
            return True
        except Exception as e:
            print(e)
            return False

    def stop_live_view(self):
        print("Stopping live view")
        self.live = False
        self.capture_thread.join()    


def capture_images(camera, pictures_raw, i):
    images = []
    for m in range(pictures_raw):
        frame = camera.get_frame()
            
        if frame is not None:
            frame_np = frame.get_numpy()
            frame_rgb = Image.fromarray(frame_np, "RGB")
            images.append(frame_rgb)
            time.sleep(0.17)
    return images



def create_brightest_image(i, images, path):
    result_image = Image.new("RGB", images[0].size)
    result_image = reduce(ImageChops.lighter, images)
    result_image.save(path + f"bild{i+1}.jpg")
    print("Bild fertig")

def create_metafile(path, exp, picture_pause, pictures_raw):
    path = (path + "metafile.json")
    current_time = datetime.now()
    data = {
        "start": current_time.isoformat(),
        "end": current_time.isoformat(),
        "exposure": exp,
        "number of images": 0,
        "break time": picture_pause,
        "pictures raw": pictures_raw
        }

    with open(path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

def update_metafile(path):
    path = (path + "metafile.json")
    current_time = datetime.now()
    
    try:
        with open(path, 'r') as json_file:
            data = json.load(json_file)
    except FileNotFoundError:
        print("Metafile could not be found and was not updated")
        return
    data["number of images"] += 1
    data["end"] = current_time.isoformat()
    
    with open(path, 'w') as json_datei:
        json.dump(data, json_datei, indent=4)

    
def main():
    skript_verzeichnis = os.path.dirname(os.path.abspath(__file__))
    os.chdir(skript_verzeichnis)
    config = configparser.ConfigParser()
    config.read('config.ini')
    camera = IDSCamera()
    camera.open_camera(0)
    camera.prepare_acquisition()
    camera.start_acquisition()
    exp = config.get('Settings', 'exposure')
    exp = float(exp)
    camera.set_exposure(exp)
    pictures_raw = config.get('Settings', 'pictures_raw')
    pictures_raw = int(pictures_raw)
    picture_pause = config.get('Settings', 'picture_pause')
    picture_pause = int(picture_pause)
    path = config.get('Settings', 'path_for_images')
    create_metafile(path, exp, picture_pause, pictures_raw)
    i = 0
    while True:        
        start_timer = time.time()
        images = capture_images(camera, pictures_raw, i)
        create_brightest_image(i, images, path)
        update_metafile(path)
        end_timer = time.time()
        elapsed_time = end_timer - start_timer
        if elapsed_time > picture_pause:
            print(f"The time required for image processing is longer than the break.({elapsed_time})")
            break
        pause = picture_pause-elapsed_time
        print(f"Picture {i+1} taken. Pause: {pause:.2f} seconds.")
        time.sleep(pause)
        i += 1

if __name__ == "__main__":
    main()