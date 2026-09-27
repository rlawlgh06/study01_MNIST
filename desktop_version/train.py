"""
MNIST 손글씨 숫자 데이터로 CNN 모델을 학습하고, 학습된 가중치를 mnist_cnn.pt 파일로 저장합니다.

실행 방법:
    python train.py             # 기본 3 에폭 학습
    python train.py --에폭 5    # 에폭 수를 바꿔서 학습
"""

import argparse
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from torch import optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from model import 숫자인식CNN

# 이 파일이 있는 폴더 기준 경로 (어디서 실행해도 같은 위치를 쓰도록 함)
현재폴더 = Path(__file__).resolve().parent
가중치파일 = 현재폴더 / "mnist_cnn.pt"
데이터폴더 = 현재폴더 / "data"


def 데이터_준비(배치크기: int, 평가배치크기: int):
    """MNIST 데이터셋을 내려받아 학습용/평가용 데이터로더를 만들어 돌려줍니다."""
    # 이미지를 텐서로 바꾸고, MNIST 전체 평균(0.1307)과 표준편차(0.3081)로 정규화합니다.
    전처리 = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])

    학습데이터 = datasets.MNIST(root=str(데이터폴더), train=True, download=True, transform=전처리)
    평가데이터 = datasets.MNIST(root=str(데이터폴더), train=False, download=True, transform=전처리)

    학습로더 = DataLoader(학습데이터, batch_size=배치크기, shuffle=True)
    평가로더 = DataLoader(평가데이터, batch_size=평가배치크기, shuffle=False)
    return 학습로더, 평가로더


def 한_에폭_학습(모델, 장치, 학습로더, 옵티마이저, 에폭번호: int):
    """학습 데이터 전체를 한 번 훑으면서 모델 가중치를 갱신합니다."""
    모델.train()  # 드롭아웃을 켜는 학습 모드
    총손실 = 0.0

    for 배치번호, (이미지, 정답) in enumerate(학습로더, start=1):
        이미지, 정답 = 이미지.to(장치), 정답.to(장치)

        옵티마이저.zero_grad()              # 이전 기울기 초기화
        예측 = 모델(이미지)                 # 순전파
        손실 = F.cross_entropy(예측, 정답)  # 교차 엔트로피 손실 계산
        손실.backward()                     # 역전파로 기울기 계산
        옵티마이저.step()                   # 가중치 갱신

        총손실 += 손실.item()
        if 배치번호 % 100 == 0:
            진행률 = 100.0 * 배치번호 / len(학습로더)
            print(f"  [에폭 {에폭번호}] 진행률 {진행률:5.1f}%  손실 {손실.item():.4f}")

    print(f"  [에폭 {에폭번호}] 평균 학습 손실: {총손실 / len(학습로더):.4f}")


def 성능_평가(모델, 장치, 평가로더) -> float:
    """평가 데이터로 정확도를 측정해 백분율로 돌려줍니다."""
    모델.eval()  # 드롭아웃을 끄는 평가 모드
    총손실 = 0.0
    맞힌개수 = 0

    with torch.no_grad():  # 평가할 때는 기울기를 계산하지 않음
        for 이미지, 정답 in 평가로더:
            이미지, 정답 = 이미지.to(장치), 정답.to(장치)
            예측 = 모델(이미지)
            총손실 += F.cross_entropy(예측, 정답, reduction="sum").item()
            예측숫자 = 예측.argmax(dim=1)
            맞힌개수 += (예측숫자 == 정답).sum().item()

    전체개수 = len(평가로더.dataset)
    정확도 = 100.0 * 맞힌개수 / 전체개수
    print(f"  평가 결과 → 평균 손실 {총손실 / 전체개수:.4f}, "
          f"정확도 {맞힌개수}/{전체개수} ({정확도:.2f}%)")
    return 정확도


def main():
    파서 = argparse.ArgumentParser(description="MNIST 손글씨 숫자 인식 모델 학습")
    파서.add_argument("--에폭", type=int, default=3, help="학습 반복 횟수 (기본값 3)")
    파서.add_argument("--배치크기", type=int, default=128, help="학습 배치 크기 (기본값 128)")
    파서.add_argument("--학습률", type=float, default=1e-3, help="Adam 학습률 (기본값 0.001)")
    설정 = 파서.parse_args()

    # 그래픽카드(CUDA)를 쓸 수 있으면 사용하고, 없으면 CPU로 학습합니다.
    장치 = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"사용 장치: {장치}")

    torch.manual_seed(1)  # 결과 재현을 위한 난수 고정

    print("MNIST 데이터를 준비합니다...")
    학습로더, 평가로더 = 데이터_준비(설정.배치크기, 1000)

    모델 = 숫자인식CNN().to(장치)
    옵티마이저 = optim.Adam(모델.parameters(), lr=설정.학습률)

    시작시각 = time.time()
    for 에폭 in range(1, 설정.에폭 + 1):
        print(f"\n=== 에폭 {에폭}/{설정.에폭} ===")
        한_에폭_학습(모델, 장치, 학습로더, 옵티마이저, 에폭)
        성능_평가(모델, 장치, 평가로더)

    걸린시간 = time.time() - 시작시각
    print(f"\n학습 완료 (총 {걸린시간:.1f}초)")

    # 학습된 가중치만 저장합니다. (모델 구조는 model.py에 있음)
    torch.save(모델.state_dict(), 가중치파일)
    print(f"가중치를 저장했습니다: {가중치파일}")


if __name__ == "__main__":
    main()
