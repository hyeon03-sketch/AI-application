"""Task 4 (fair comparison): detect 2D keypoints on KERAAL Group 3 videos using a crop
around the person, the same way detect2d.py does for ASPset.

Usage (on the workstation with the GPU):
    python keraal_detect_crop.py <KERAAL group3 dir> <output cache dir>

Output per video: the same .npz format as keraal_eval.py detect
(kp, conf, found, wh), so keraal_eval.py eval can read it without changes.
KERAAL is CC BY-NC-SA: keep the output cache outside the repo.
"""

# --- Standard Python tools ---
import glob   # finds files that match a pattern, e.g. all "*.avi" videos in a folder
import os     # works with file and folder paths
import sys    # lets us tell Python where else to look for code files

# --- Extra libraries ---
import cv2          # OpenCV: reads video files frame by frame
import numpy as np  # numbers and arrays (tables of numbers)

# --- Find Sonny's code so we can reuse it ---
# HERE = the folder this file is in (members/roshini/fair_comparison)
HERE = os.path.dirname(os.path.abspath(__file__))
# SONNY = Sonny's mocap3d folder: go up two folders (to members/), then into sonny/mocap3d
SONNY = os.path.join(HERE, "..", "..", "sonny", "mocap3d")
# Put Sonny's folder at the front of Python's search list, so "import detect2d" finds his file
sys.path.insert(0, SONNY)

# Reuse from detect2d.py:
#   crop_square: cuts a square around a box and resizes it to CROP x CROP pixels
#   CROP: the crop size in pixels (384), the same size used for ASPset
from detect2d import crop_square, CROP

# --- Settings ---
FULL_SIZE = 960  # image size for the first pass on the whole frame (same as keraal_eval.py detect)
BATCH = 32       # how many frames we send to YOLO at once (faster than one by one)


def find_person_boxes(model, frames):
    """Pass 1 of 2: run YOLO on the WHOLE frame to find a box around the person.

    model:  the YOLO11x-pose model
    frames: list of video frames (images)
    Returns:
        boxes   (F, 4): one box per frame, as x1, y1, x2, y2 in pixels (top-left and bottom-right corners)
        has_box (F,):   True if a person was found in that frame, False if not
    """
    n = len(frames)                 # number of frames in the video
    boxes = np.zeros((n, 4))        # empty table for the boxes: n rows, 4 numbers each
    has_box = np.zeros(n, bool)     # empty True/False list, all False to start

    # go through the video 32 frames at a time
    for s in range(0, n, BATCH):
        results = model(frames[s:s + BATCH], imgsz=FULL_SIZE, verbose=False)
        for i, r in enumerate(results):          # one result per frame
            if r.boxes is None or len(r.boxes) == 0:
                continue                         # no person found in this frame, skip it
            b = r.boxes.xyxy.cpu().numpy()       # all person boxes YOLO found in this frame
            areas = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])  # width x height of each box
            j = int(np.argmax(areas))            # pick the LARGEST person (same rule as keraal_eval.py)
            boxes[s + i] = b[j]
            has_box[s + i] = True
    return boxes, has_box


def fill_missing_boxes(boxes, has_box):
    """Give frames with no box a box, by drawing a straight line between the nearest
    frames that do have one (linear interpolation). Same idea Sonny uses for missing joints.

    Example: frame 10 box left edge = 100, frame 12 = 120, frame 11 missing -> frame 11 gets 110.
    """
    if not has_box.any():
        return boxes                    # no person in the whole video: nothing we can fill
    idx = np.arange(len(boxes))         # frame numbers 0, 1, 2, ...
    filled = boxes.copy()               # copy, so we don't change the original table
    for c in range(4):                  # do it for each of the 4 numbers (x1, y1, x2, y2)
        filled[:, c] = np.interp(idx, idx[has_box], boxes[has_box, c])
    return filled


def detect_on_crops(model, frames, boxes):
    """Pass 2 of 2: cut a square crop around each person box and find the 17 joints on it,
    exactly like detect2d.py does for ASPset.

    model:  the YOLO11x-pose model
    frames: list of video frames (images)
    boxes:  (F, 4) person box per frame, from find_person_boxes + fill_missing_boxes
    Returns (the same format as keraal_eval.py detect):
        kp    (F, 17, 2): x, y of the 17 COCO joints in FULL-FRAME pixels
        conf  (F, 17):    how sure YOLO is about each joint (0 to 1)
        found (F,):       True if YOLO found a person on the crop
    """
    n = len(frames)
    kp = np.zeros((n, 17, 2))      # empty table: n frames x 17 joints x (x, y)
    conf = np.zeros((n, 17))       # empty table: n frames x 17 confidences
    found = np.zeros(n, bool)      # True/False per frame, all False to start
    buf, meta = [], []             # buf = crops waiting to go to YOLO; meta = how to undo each crop

    def flush():
        """Send the waiting crops to YOLO, then turn the joints back into full-frame pixels."""
        # half=True and imgsz=CROP: the same settings detect2d.py uses for ASPset
        results = model(buf, imgsz=CROP, verbose=False, half=True)
        for r, (fi, x0, y0, s) in zip(results, meta):
            if r.keypoints is None or len(r.boxes) == 0:
                continue                                   # no person on this crop
            b = r.boxes.xyxy.cpu().numpy()                 # person boxes YOLO found on the crop
            # distance from each person's box centre to the crop centre
            d = np.hypot((b[:, 0] + b[:, 2]) / 2 - CROP / 2, (b[:, 1] + b[:, 3]) / 2 - CROP / 2)
            # pick the person nearest the centre (the crop was centred on our person);
            # the tiny confidence term only breaks ties. Same rule as detect2d.py.
            j = int(np.argmin(d - 1e-3 * r.boxes.conf.cpu().numpy()))
            # undo the crop: "/ s" undoes the resize, "+ [x0, y0]" undoes the shift
            kp[fi] = r.keypoints.xy[j].cpu().numpy() / s + [x0, y0]
            conf[fi] = r.keypoints.conf[j].cpu().numpy()
            found[fi] = True
        buf.clear(), meta.clear()                           # empty the waiting list

    for fi in range(n):
        # crop_square (from detect2d.py) returns the crop and how it was made:
        # x0, y0 = where the crop starts in the full frame, s = how much it was resized
        c, x0, y0, s = crop_square(frames[fi], boxes[fi])
        buf.append(c), meta.append((fi, x0, y0, s))
        if len(buf) == BATCH:                               # 32 crops waiting: send them
            flush()
    if buf:                                                 # send the last few crops
        flush()
    return kp, conf, found


def detect_video(model, video):
    """Run pass 1 and pass 2 on one KERAAL video.
    Returns kp, conf, found (see detect_on_crops) and wh = [width, height] of the video."""
    # read every frame of the video into a list (same as keraal_eval.py detect)
    cap = cv2.VideoCapture(video)
    frames = []
    while True:
        ok, img = cap.read()
        if not ok:                       # no more frames
            break
        frames.append(img)
    cap.release()
    h, w = frames[0].shape[:2]           # video height and width in pixels (540, 960 for KERAAL)

    boxes, has_box = find_person_boxes(model, frames)      # pass 1: whole frame -> person box
    if not has_box.any():
        # nobody found in the whole video: return "not found" for every frame
        n = len(frames)
        return np.zeros((n, 17, 2)), np.zeros((n, 17)), np.zeros(n, bool), np.array([w, h]), 0.0
    boxes = fill_missing_boxes(boxes, has_box)              # fill frames where the box was missed
    kp, conf, found = detect_on_crops(model, frames, boxes)  # pass 2: crop -> 17 joints
    return kp, conf, found, np.array([w, h]), has_box.mean()


def main(g3, cache):
    """Detect every KERAAL Group 3 video and save one .npz per video in `cache`."""
    from ultralytics import YOLO          # imported here, so --check runs without ultralytics
    os.makedirs(cache, exist_ok=True)     # make the output folder if it doesn't exist yet
    model = YOLO("yolo11x-pose.pt")       # the same model as ASPset and keraal_eval.py
    vids = sorted(glob.glob(os.path.join(g3, "videos", "*.avi")))  # all KERAAL G3 videos
    for k, vid in enumerate(vids):
        # same file name as keraal_eval.py detect, so keraal_eval.py eval can read this folder
        out = os.path.join(cache, os.path.basename(vid)[:-4] + ".npz")
        if os.path.exists(out):
            continue                      # already done (useful if the run is restarted)
        kp, conf, found, wh, box_rate = detect_video(model, vid)
        np.savez_compressed(out, kp=kp, conf=conf, found=found, wh=wh)
        print(f"{k + 1}/{len(vids)} {os.path.basename(vid)} frames {len(found)} "
              f"box found {box_rate:.3f} joints found {found.mean():.3f}", flush=True)


def _check():
    """Quick self-test with a FAKE model (no GPU, no data needed).
    The fake model puts one person's joints at the centre of every image it gets."""
    class T:                               # tiny stand-in for a GPU tensor
        def __init__(self, a): self.a = np.asarray(a, float)
        def cpu(self): return self
        def numpy(self): return self.a
        def __getitem__(self, i): return T(self.a[i])

    class Result:                          # what YOLO returns for one image
        def __init__(self, size):
            c = size / 2                   # image centre
            self.boxes = type("B", (), {})()
            self.boxes.xyxy = T([[c - 40, c - 40, c + 40, c + 40], [0, 0, 30, 30]])  # centre person + corner person
            self.boxes.conf = T([0.9, 0.95])
            self.boxes.__class__.__len__ = lambda s: 2
            self.keypoints = type("K", (), {})()
            xy = np.zeros((2, 17, 2)); xy[0] = c; xy[1] = 10
            self.keypoints.xy, self.keypoints.conf = T(xy), T(np.full((2, 17), 0.8))

    class FakeModel:
        def __call__(self, imgs, imgsz, **kw):
            return [Result(imgsz if imgsz == CROP else img.shape[1]) for img in imgs]

    frames = [np.zeros((540, 960, 3), np.uint8) for _ in range(40)]   # 40 black KERAAL-size frames
    # pass 1 should find a box in every frame, and fill_missing_boxes should fill a gap
    boxes, has_box = find_person_boxes(FakeModel(), frames)
    assert has_box.all()
    has_box[5] = False
    assert np.allclose(fill_missing_boxes(boxes, has_box)[5], boxes[4])
    # pass 2 on a known box centred at (500, 300) should give joints at (500, 300)
    kp, conf, found = detect_on_crops(FakeModel(), frames, np.tile([400., 100, 600, 500], (40, 1)))
    assert found.all() and np.allclose(kp[:, 0], [500, 300])
    print("keraal_detect_crop --check OK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        _check()                          # python keraal_detect_crop.py --check
    elif len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])    # python keraal_detect_crop.py <group3 dir> <cache dir>
    else:
        print(__doc__)                    # wrong arguments: show how to use the file
