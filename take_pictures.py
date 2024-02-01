import cv2
import time
import os
from PIL import Image
import numpy as np


def camera_setup():
    cap = cv2.VideoCapture(0)  # öffnet die Kamera (0 ist standardmäßig)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # setzt den Puffer auf 1 Bild
    return cap

def capture_images(cap, pictures_raw, i):
    images = []
    
    for m in range(pictures_raw):
        ret, frame = cap.read()
        # image_path = os.path.join(save_path, f"bild{i+1}-{m+1}.jpg")
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        images.append(frame)
    
        # cv2.imwrite(image_path, frame)
        time.sleep(0.17)
    return images


def create_brightest_image(i, images):
    # Öffnen Sie alle Bilder einmalig außerhalb der Schleife


    # Initialisieren Sie ein leeres Bild mit der gleichen Auflösung wie die Eingangsbilder
    result_image = Image.new("RGB", (images[0].shape[1], images[0].shape[0]))

    # Durchlaufen Sie jede Position im Bild
    for y in range(result_image.size[1]):
        for x in range(result_image.size[0]):
            # Wählen Sie den hellsten Pixel aus allen Bildern an dieser Position aus
            brightest_pixel = np.max([img[y, x, :] for img in images], axis=0)

            # Setzen Sie den hellsten Pixel im Ergebnisbild
            result_image.putpixel((x, y), tuple(brightest_pixel))

    # Speichern Sie das Ergebnisbild
    result_image.save(f"/home/gruenspecht/Bilder/Timelaps/timelaps1/bild{i+1}.jpg")
    print("Bild fertig")


def main():
    cap = camera_setup()

    if not cap.isOpened():
        print("Error: Die Kamera konnte nicht geöffnet werden.")
        return
 
    pictures_raw = 40           # number of pictures for a "bright" picture
    picture_pause = 120          # in seconds
    i = 0
    while True:        
        for reset in range(3):
            ret, frame = cap.read()
        start_timer = time.time()
        images = capture_images(cap, pictures_raw, i)
        create_brightest_image(i, images)
        end_timer = time.time()
        elapsed_time = end_timer - start_timer
        if elapsed_time > picture_pause:
            print("The time required for image processing is longer than the break.")
            break
        pause = picture_pause-elapsed_time
        print(f"Picture {i+1} taken. Pause: {pause:.2f} seconds.")
        time.sleep(pause)
        i += 1


    cap.release()  # Schließe die Kommunikation mit der Kamera

    # Schließe alle offenen Fenster
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()