#-----------------------------------------
# Python Raspberry Pi
# SecruiPi Project
#-----------------------------------------
# Abstract: TODO(kirkcw)
#-----------------------------------------
# Authors:
#   Kirk Worley
#   Alexander Morales
#   Austin Martinez
#   Brittany Arnold
#-----------------------------------------
# Note: When in debug mode,
#       press 'q' to quit.
#-----------------------------------------

from picamera.array import PiRGBArray
from picamera import PiCamera
from utility import send_email, TempImage
import warnings
import datetime
import argparse
import json
import cv2
import time
import os

# Args Parser construction.
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True,
        help="Path to JSON Config")
ap.add_argument("-d", "--debug", required=False,
        help="Debugging Mode True/False")
args = vars(ap.parse_args())

# Filter warnings.
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
client = None

if args['debug']:
        print('> Debugging mode is on!')
        debug_mode = True
else:
        debug_mode = False

# Initialize camera and get raw capture data.
camera = PiCamera()
camera.resolution = tuple(conf['resolution'])
camera.framerate = conf['fps']
rawCapture = PiRGBArray(camera, size=tuple(conf['resolution']))

# Initialize last frame and motion counter.
print '[INFO] Warming up...'
time.sleep(conf['camera_warmup_time'])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0
print('[INFO] SecuriPi started!')

# Get frames for camera data.
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
        frame = f.array
        timestamp = datetime.datetime.now()
        text = 'Unoccupied.'

        #---Computer Vision---
        # Resize frame, blur, convert to greyscale.
        grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        grey = cv2.GaussianBlur(grey, tuple(conf['blur_size']), 0)

        if avg is None:
                print '[INFO] Starting a background model.'
                avg = grey.copy().astype('float')
                rawCapture.truncate(0)
                continue

        # Gather weighted avg of current and previous frames. Compute difference
        # between frame and avg.
        frameDelta = cv2.absdiff(grey, cv2.convertScaleAbs(avg))
        cv2.accumulateWeighted(grey, avg, 0.5)

        # Threshold the delta image, dilate to remove holes and find contours.
        thresh = cv2.threshold(frameDelta, conf['delta_thresh'], 255,
                cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        im2, conts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE)

        for c in conts:
                if cv2.contourArea(c) < conf["min_area"]:
                        continue

                # Compute bounding box using cv, draw, and update the text.
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                text = 'Occupied.'

        # Write text and timestamp to frame.
        ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
        cv2.putText(frame, "Room Status: {}".format(text), (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
                0.35, (0, 0, 255), 1)

        #---Logic---
        if text == 'Occupied':
                cv2.imwrite('/tmp/securipi_{}.jpg'.format(motionCounter), frame);

                if (timestamp - lastUploaded).seconds >= conf['min_upload_seconds']:
                        motionCounter += 1;
                        if motionCounter >= int(conf['min_motion_frames']):

                                if conf['use_email']:
                                        print('[ALERT] Sending an alert email!')
                                        send_email(conf)
                                        print('[INFO] waiting {} seconds...'.format(conf['camera_warmup_time']))
                                        time.sleep(conf['camera_warmup_time'])
                                        print('[INFO] Resuming...')

                                lastUploaded = timestamp
                                motionCounter = 0

        # Room not occupied.
        else:
                motionCounter = 0

        # Frames displayed to screen?
        if conf['show_video']:
                cv2.imshow('Security Feed', frame)
                key = cv2.waitKey(1) & 0xFF

                if debug_mode:
                        cv2.imshow('Debug blurred grey frame:', grey)
                        cv2.imshow('Debug threshold frame:', thresh)

                if key == ord('q'):
                        break

        # Clear the stream in preparation for the next frame.
        rawCapture.truncate(0)
