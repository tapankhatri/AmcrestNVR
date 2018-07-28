#!/usr/bin/env python3

import os

from moviepy.editor import VideoFileClip, concatenate_videoclips


def concatenateVideos(dirName, outputName):
    dirName=os.path.abspath(dirName)
    print(dirName)
    mp4Files = [dirName+"/"+f for f in os.listdir(dirName) if f.endswith('.mp4')]
    mp4Files = sorted(mp4Files)
    print(mp4Files)

    print("Starting to create VideoFileClip Array")
    mp4VideoFileClips = [VideoFileClip(mp4File) for mp4File in mp4Files]
    print("Finished creating VideoFileClip Array")

    print("Started creating final clip")
    final_clip = concatenate_videoclips(mp4VideoFileClips)
    print("Ended creating final clip")

    print("Started writing mp4 file")
    final_clip.write_videofile(dirName+"/"+outputName+".mp4", audio=False)
    print("Finished writing mp4 file")

    return True


#concatenateVideos("/Users/aa66428/Desktop/Projects/Development/RaspberryPi/NVR/videos/", "outputFile")
