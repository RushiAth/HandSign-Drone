import json
import torch
import torch2trt
from torch2trt import TRTModule
import time
import ipywidgets
from IPython.display import display
import cv2
import torchvision.transforms as transforms
import PIL.Image
import trt_pose.coco
import trt_pose.models
from trt_pose.draw_objects import DrawObjects
from trt_pose.parse_objects import ParseObjects
from jetcam.usb_camera import USBCamera
from jetcam.utils import bgr8_to_jpeg

with open('models/human_pose.json', 'r') as f:
    human_pose = json.load(f)

topology = trt_pose.coco.coco_category_to_topology(human_pose)

print("topology created")

num_parts = len(human_pose['keypoints'])
num_links = len(human_pose['skeleton'])

model = trt_pose.models.resnet18_baseline_att(num_parts, 2 * num_links).cuda().eval()

MODEL_WEIGHTS = 'models/resnet18_baseline_att_224x224_A_epoch_249.pth'

model.load_state_dict(torch.load(MODEL_WEIGHTS))

print("model weights loaded")

WIDTH = 640
HEIGHT = 360

data = torch.zeros((1, 3, HEIGHT, WIDTH)).cuda()

print("start optimizing model")

# model_trt = torch2trt.torch2trt(model, [data], default_device_type=torch2trt.trt.DeviceType.DLA, dla_core=1, fp16_mode=True, max_workspace_size=1<<25, dla=False)

# print("finish optimizing model")

# OPTIMIZED_MODEL = 'models/resnet18_baseline_att_224x224_A_epoch_249_trt.pth'

# torch.save(model_trt.state_dict(), OPTIMIZED_MODEL)


# model_trt = TRTModule()
# model_trt.load_state_dict(torch.load(OPTIMIZED_MODEL))


t0 = time.time()
torch.cuda.current_stream().synchronize()
for i in range(50):
    y = model(data)
torch.cuda.current_stream().synchronize()
t1 = time.time()

print(50.0 / (t1 - t0))

mean = torch.Tensor([0.485, 0.456, 0.406]).cuda()
std = torch.Tensor([0.229, 0.224, 0.225]).cuda()
device = torch.device('cuda')

print("random statistics calculated")

def preprocess(image):
    global device
    device = torch.device('cuda')
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = PIL.Image.fromarray(image)
    image = transforms.functional.to_tensor(image).to(device)
    image.sub_(mean[:, None, None]).div_(std[:, None, None])
    return image[None, ...]


parse_objects = ParseObjects(topology)
draw_objects = DrawObjects(topology)


camera = USBCamera(width=WIDTH, height=HEIGHT, capture_fps=30)
# camera = CSICamera(width=WIDTH, height=HEIGHT, capture_fps=30)

camera.running = True

image_w = ipywidgets.Image(format='jpeg')

def execute(change):
    print("new frame arrived")
    image = change['new']
    data = preprocess(image)
    cmap, paf = model(data)
    cmap, paf = cmap.detach().cpu(), paf.detach().cpu()
    counts, objects, peaks = parse_objects(cmap, paf)#, cmap_threshold=0.15, link_threshold=0.15)
    print("number of poses found: " + str(counts))
    draw_objects(image, counts, objects, peaks)
    image_w.value = bgr8_to_jpeg(image[:, ::-1, :])
    f = open('image.jpg','wb')
    f.write(image_w.value)
    f.close()
    # img = PIL.Image.frombytes("RGB", (224, 224), image_w.value)
    # img.save("test.jpg")
    
execute({'new': camera.value})

while True:
    camera.observe(execute, names='value')

camera.unobserve_all()
