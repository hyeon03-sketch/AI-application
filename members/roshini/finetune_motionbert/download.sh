#!/bin/bash
# Downloads MotionBERT's code, its pretrained weights and the public data bundle into the current folder.
# Safe to run again: anything already there is skipped.
set -e
[ -d MotionBERT ] || git clone -q https://github.com/Walter0807/MotionBERT.git
W=MotionBERT/checkpoint/pose3d/FT_MB_release_MB_ft_h36m
mkdir -p $W
[ -f $W/best_epoch.bin ] || curl -sL -o $W/best_epoch.bin \
  https://huggingface.co/walterzhu/MotionBERT/resolve/main/checkpoint/pose3d/FT_MB_release_MB_ft_h36m/best_epoch.bin
[ -d Mocap3D_preprocessed_1118 ] || (curl -sL -o data.zip \
  https://github.com/hyeon03-sketch/AI-application/releases/download/data-1118/Mocap3D_preprocessed_1118.zip && unzip -q data.zip)
ls -lh $W
