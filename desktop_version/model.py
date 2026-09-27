"""
MNIST 손글씨 숫자 인식용 합성곱 신경망(CNN) 모델 정의 파일입니다.
학습 스크립트(train.py)와 손글씨 입력 프로그램(draw_predict.py)이 이 파일을 함께 사용합니다.
"""

import torch.nn as nn
import torch.nn.functional as F


class 숫자인식CNN(nn.Module):
    """28x28 크기의 흑백 손글씨 이미지를 0~9 중 하나로 분류하는 CNN 모델입니다."""

    def __init__(self):
        super().__init__()
        # 첫 번째 합성곱 층: 입력 1채널(흑백) -> 출력 32채널, 3x3 필터
        self.합성곱1 = nn.Conv2d(in_channels=1, out_channels=32, kernel_size=3)
        # 두 번째 합성곱 층: 32채널 -> 64채널, 3x3 필터
        self.합성곱2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3)
        # 과적합을 줄이기 위한 드롭아웃 층
        self.드롭아웃1 = nn.Dropout(0.25)
        self.드롭아웃2 = nn.Dropout(0.5)
        # 완전연결 층: 12*12*64 = 9216개의 특징을 128차원으로 압축
        self.완전연결1 = nn.Linear(9216, 128)
        # 최종 출력 층: 128차원 -> 숫자 10개(0~9)
        self.완전연결2 = nn.Linear(128, 10)

    def forward(self, 입력):
        """순전파 과정을 정의합니다. 입력 크기는 (배치, 1, 28, 28)입니다."""
        출력 = self.합성곱1(입력)          # (배치, 32, 26, 26)
        출력 = F.relu(출력)
        출력 = self.합성곱2(출력)          # (배치, 64, 24, 24)
        출력 = F.relu(출력)
        출력 = F.max_pool2d(출력, 2)       # (배치, 64, 12, 12) 크기를 절반으로 줄임
        출력 = self.드롭아웃1(출력)
        출력 = 출력.flatten(1)             # (배치, 9216) 1차원으로 펼침
        출력 = F.relu(self.완전연결1(출력))
        출력 = self.드롭아웃2(출력)
        출력 = self.완전연결2(출력)        # (배치, 10) 각 숫자에 대한 점수(로짓)
        return 출력
