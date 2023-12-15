#!/usr/bin/env python3

import asyncio
import jetson.inference
from jetson_tello import run_jetson_tello_app
import numpy as np

count = 0
takePhoto = False
tol = 0.4
detected_pose = -1

pose_detector = jetson.inference.poseNet(network="densenet121-body", threshold=0.5)


def detect_faces_and_objects(drone, frame, cuda):
    global takePhoto, count, detected_pose

    if not takePhoto:
        return

    poses = pose_detector.Process(cuda, overlay='keypoints,links')

    if len(poses) > 0:

        keypoints = []

        for pose in poses:
            keypoints.extend(pose.Keypoints)

        detected_pose = detect_pose(keypoints)

    takePhoto = False

# returns index of the pose being done
def detect_pose(pose_keypoints):
    global detected_pose

    kpts = {}
    for p in pose_keypoints:
        kpts[p.ID] = np.asarray([p.x, p.y])
    # pose 0: right arm extended

    # right arm landmarks found
    # points of interest: right shoulder (id6), right elbow (id8), right wrist (id10)
    if 6 in kpts and 8 in kpts and 10 in kpts:
        # flip: left or right arm on head
        # elbow x < shoulder x < wrist x
        shoulder_between_wrist_elbow_right = (kpts[8][0] < kpts[6][0] and kpts[6][0] < kpts[10][0]) or (kpts[8][0] > kpts[6][0] and kpts[6][0] > kpts[10][0])
        if kpts[10][1] < kpts[6][1] and shoulder_between_wrist_elbow_right:
            return 3

        forearm = kpts[10] - kpts[8]
        upper_arm = kpts[6] - kpts[8]

        cos_angle = np.dot(forearm, upper_arm) / \
            (np.linalg.norm(forearm) * np.linalg.norm(upper_arm))

        slope = (kpts[10][1] - kpts[6][1]) / (kpts[10][0] - kpts[6][0])

        # pose 0: right arm extended
        if cos_angle < -1 + tol:
            if abs(slope) < 0.5:
                return 0

        if abs(cos_angle) < tol:
            if kpts[10][1] < kpts[8][1]:
                return 1
            else:
                return 2

    # left arm landmarks found
    # points of interest: left shoulder (id5), left elbow (id7), left wrist (id9)
    if 5 in kpts and 7 in kpts and 9 in kpts:
        # flip: left or right arm on head
        # elbow x < shoulder x < wrist x
        shoulder_between_wrist_elbow_left = (kpts[7][0] < kpts[5][0] and kpts[5][0] < kpts[9][0]) or (kpts[7][0] > kpts[5][0] and kpts[5][0] > kpts[9][0])
        if kpts[9][1] < kpts[5][1] and shoulder_between_wrist_elbow_left:
            return 3

        forearm = kpts[9] - kpts[7]
        upper_arm = kpts[5] - kpts[7]

        cos_angle = np.dot(forearm, upper_arm) / \
            (np.linalg.norm(forearm) * np.linalg.norm(upper_arm))

        slope = (kpts[9][1] - kpts[5][1]) / (kpts[9][0] - kpts[5][0])

        # pose 0: left arm extended
        if cos_angle < -1 + tol:
            if abs(slope) < 0.5:
                return 0

        if abs(cos_angle) < tol:
            if kpts[9][1] < kpts[7][1]:
                return 1
            else:
                return 2
        
    return -1

async def fly(drone):
    global takePhoto, detected_pose

    await drone.takeoff()
    await drone.move_up(80)
    while True:
        if not takePhoto:
            print("Analyzing detection")
            if detected_pose == 0:
                await drone.turn_counterclockwise(90)
                await drone.turn_clockwise(90)
            elif detected_pose == 1:
                await drone.turn_clockwise(90)
                await drone.turn_counterclockwise(90)
            elif detected_pose == 2:
                await drone.land()
                break
            elif detected_pose == 3:
                await drone.flip_back()
            detected_pose = -1
            takePhoto = True
        else:
            print("Waiting for detection")
        await asyncio.sleep(0.1)

run_jetson_tello_app(fly, process_frame=detect_faces_and_objects)
