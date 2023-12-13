#!/usr/bin/env python3

import asyncio
import jetson.inference
from jetson_tello import run_jetson_tello_app
# from jetson.utils import videoOutput
from PIL import Image
import numpy as np
import random

count = 0
takePhoto = False
tol = 0.4
detected_pose = -1

# face_detector = jetson.inference.detectNet("facenet", threshold=0.5)
pose_detector = jetson.inference.poseNet(network="densenet121-body", threshold=0.5)
# output = videoOutput("rtp://192.168.55.1:8080")

# def get_coors(topology, image, object_counts, objects, normalized_peaks):
#     height = image.shape[0]
#     width = image.shape[1]

#     list_of_coors = []

#     K = topology.shape[0]
#     count = int(object_counts[0])
#     K = topology.shape[0]
#     for i in range(count):
#         color = (0, 255, 0)
#         obj = objects[0][i]
#         C = obj.shape[0]
#         for j in range(C):
#             k = int(obj[j])
#             if k >= 0:
#                 peak = normalized_peaks[0][j][k]
#                 x = round(float(peak[1]) * width)
#                 y = round(float(peak[0]) * height)
#                 list_of_coors.append(x)
#                 list_of_coors.append(y)
#             else:
#                 list_of_coors.append(-1)
#                 list_of_coors.append(-1)


def detect_faces_and_objects(drone, frame, cuda):
    global takePhoto, count, detected_pose

    if not takePhoto:
        return


    # face_detections = face_detector.Process(cuda)
    poses = pose_detector.Process(cuda, overlay='keypoints,links')
    # print('poses:')
    # for pose in poses:
    #     print(pose.Keypoints)
    #     print('Links', pose.Links)

    # print("detected {:d} objects in image".format(len(poses)))
    
    # jetson.utils.saveImageRGBA(
    #         f"./images/image{count}.jpg", cuda, 960, 720)

    if len(poses) > 0:

        keypoints = []

        for pose in poses:
            keypoints.extend(pose.Keypoints)

        detected_pose = detect_pose(keypoints)

        poseNames = ["ArmExtended", "AngleUp", "AngleDown", "HeadPat", "NoDetection"]
        
        print("Detected Pose: ", poseNames[detected_pose])

        jetson.utils.saveImageRGBA(
            f"./images/{poseNames[detected_pose]}{count}.jpg", cuda, 960, 720)
        # with open(f"./poses/pose{count}.txt", "w") as f:
        #     for pose in poses:
        #         f.write("Keypoints:\n" + str(pose.Keypoints) + "\n")
        #         f.write("Links:\n" + str(pose.Links) + "\n")
        #         f.write("\n")
        #     f.write("Detected Pose: " + str(detected_pose) + "\n")

        # print(pose_similarity(poses[0].Keypoints, poses[0].Keypoints))

        # if prev_poses is not None:
        #     pose_similarity(poses[0].Keypoints, prev_poses[0].Keypoints)

        # prev_poses = poses
        
        count += 1

    # render the image
    # output.Render(cuda)

    # print out performance info
    # pose_detector.PrintProfilerTimes()

    # for d in face_detections:
    # print(d)

    # count = 0

    # if (img):
    # for f in face_detections:
    #     face_img = img.crop((f.Left, f.Top, f.Right, f.Bottom))
    #     face_img.save('face_' + count + '.png')
    #     count += 1

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

        # pose 1: right arm in right angle upwards
        if abs(cos_angle) < tol:
            if kpts[10][1] < kpts[8][1]:
                return 1
            else:
                return 2
            

    # left arm landmarks found
    # points of interest: right shoulder (id5), right elbow (id7), right wrist (id9)
    if 5 in kpts and 7 in kpts and 9 in kpts:
        # flip: left arm on head
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

        # pose 1: left arm in right angle upwards
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
