"""
마우스로 숫자를 직접 써서 입력하면, 학습된 CNN 모델(mnist_cnn.pt)이 그 숫자를 인식하는 프로그램입니다.

실행 방법:
    python draw_predict.py

사용법:
    - 왼쪽 검은 칠판 위에 마우스를 끌어 숫자 하나를 크게 씁니다.
    - 손을 떼면 자동으로 인식 결과가 오른쪽에 표시됩니다.
    - [지우기] 버튼 또는 C 키를 누르면 칠판이 초기화됩니다.
    - [인식하기] 버튼 또는 Enter 키를 누르면 다시 인식합니다.
"""

import sys
import tkinter as tk
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw

from model import 숫자인식CNN

# ---------------------------------------------------------------------------
# 설정값
# ---------------------------------------------------------------------------
현재폴더 = Path(__file__).resolve().parent
가중치파일 = 현재폴더 / "mnist_cnn.pt"
아이콘파일 = 현재폴더 / "아이콘.ico"

칠판크기 = 280        # 화면에 보이는 그림판의 한 변 길이(픽셀)
붓두께 = 20           # 마우스로 그릴 때의 선 굵기
한글글꼴 = "Malgun Gothic"  # 윈도우 기본 한글 글꼴

# 작업 표시줄에서 이 앱을 파이썬과 구분되는 독립 프로그램으로 인식하게 하는 식별자입니다.
# 바로가기(.lnk)에도 같은 값을 넣어 두면 작업 표시줄 고정이 정상 동작합니다.
앱식별자 = "HanyangWomens.MNIST.HandwritingRecognizer.1"


def 작업표시줄_아이콘_설정(창=None):
    """윈도우 작업 표시줄에 앱 전용 아이콘과 식별자가 표시되도록 설정합니다."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(앱식별자)
        except Exception:
            pass  # 설정에 실패해도 프로그램 실행에는 문제가 없습니다.
    if 창 is not None and 아이콘파일.exists():
        try:
            창.iconbitmap(default=str(아이콘파일))
        except Exception:
            pass


def 오류_알림(제목: str, 내용: str):
    """콘솔 창 없이 실행(pythonw)될 때도 보이도록 오류를 메시지 상자로 띄웁니다."""
    print(f"[{제목}] {내용}")
    try:
        from tkinter import messagebox
        임시창 = tk.Tk()
        임시창.withdraw()
        messagebox.showerror(제목, 내용)
        임시창.destroy()
    except Exception:
        pass


def 모델_불러오기():
    """저장된 가중치를 읽어 평가 모드의 모델을 돌려줍니다."""
    if not 가중치파일.exists():
        오류_알림(
            "가중치 파일 없음",
            f"가중치 파일이 없습니다:\n{가중치파일}\n\n"
            "먼저 'python train.py' 를 실행해 모델을 학습해 주세요.",
        )
        sys.exit(1)

    모델 = 숫자인식CNN()
    모델.load_state_dict(torch.load(가중치파일, map_location="cpu"))
    모델.eval()  # 드롭아웃을 끄고 추론 전용 모드로 전환
    return 모델


def MNIST_형식으로_변환(그림: Image.Image):
    """
    사용자가 그린 그림을 MNIST 학습 데이터와 같은 형식으로 맞춰 줍니다.
    MNIST는 '검은 배경 + 흰 글씨'이며, 숫자를 20x20 안에 넣고
    무게중심을 28x28 이미지의 중앙에 오도록 배치한 형태입니다.
    반환값: (모델 입력 텐서, 28x28 넘파이 배열) 또는 (None, None)
    """
    # 그림판은 '흰 배경 + 검은 글씨'이므로 밝기를 반전시켜 MNIST와 같게 만듭니다.
    반전 = Image.eval(그림.convert("L"), lambda 밝기: 255 - 밝기)
    글씨영역 = 반전.getbbox()  # 글씨가 있는 최소 사각형 영역
    if 글씨영역 is None:
        return None, None  # 아무것도 그리지 않은 경우

    잘라낸그림 = 반전.crop(글씨영역)

    # 가로세로 비율을 유지한 채 긴 변을 20픽셀로 줄입니다.
    가로, 세로 = 잘라낸그림.size
    비율 = 20.0 / max(가로, 세로)
    새가로 = max(1, int(round(가로 * 비율)))
    새세로 = max(1, int(round(세로 * 비율)))
    축소그림 = 잘라낸그림.resize((새가로, 새세로), Image.LANCZOS)

    # 28x28 검은 도화지를 만들고 가운데에 붙입니다.
    도화지 = Image.new("L", (28, 28), color=0)
    도화지.paste(축소그림, ((28 - 새가로) // 2, (28 - 새세로) // 2))

    # 픽셀 무게중심을 정확히 중앙(13.5, 13.5)으로 옮깁니다. (MNIST와 동일한 방식)
    배열 = np.array(도화지, dtype=np.float32)
    총밝기 = 배열.sum()
    if 총밝기 > 0:
        y좌표, x좌표 = np.nonzero(배열)
        가중치 = 배열[y좌표, x좌표]
        중심x = (x좌표 * 가중치).sum() / 총밝기
        중심y = (y좌표 * 가중치).sum() / 총밝기
        이동x = int(round(13.5 - 중심x))
        이동y = int(round(13.5 - 중심y))
        도화지 = Image.fromarray(배열.astype(np.uint8)).transform(
            (28, 28), Image.AFFINE, (1, 0, -이동x, 0, 1, -이동y), fillcolor=0
        )
        배열 = np.array(도화지, dtype=np.float32)

    # 0~1 범위로 바꾼 뒤 MNIST 평균/표준편차로 정규화합니다.
    정규화배열 = (배열 / 255.0 - 0.1307) / 0.3081
    입력텐서 = torch.from_numpy(정규화배열).unsqueeze(0).unsqueeze(0)  # (1, 1, 28, 28)
    return 입력텐서, 배열


class 손글씨인식앱:
    """그림판과 인식 결과 화면을 담당하는 Tkinter 응용 프로그램입니다."""

    def __init__(self, 창, 모델):
        self.창 = 창
        self.모델 = 모델
        self.이전좌표 = None

        창.title("손글씨 숫자 인식기 (MNIST CNN)")
        창.resizable(False, False)

        # --- 왼쪽: 그림판 영역 ---
        왼쪽틀 = tk.Frame(창, padx=12, pady=12)
        왼쪽틀.grid(row=0, column=0)

        tk.Label(왼쪽틀, text="여기에 숫자를 크게 쓰세요", font=(한글글꼴, 12)).pack(pady=(0, 6))

        self.칠판 = tk.Canvas(왼쪽틀, width=칠판크기, height=칠판크기,
                              bg="white", cursor="pencil", highlightthickness=1,
                              highlightbackground="#888888")
        self.칠판.pack()

        단추틀 = tk.Frame(왼쪽틀)
        단추틀.pack(pady=10, fill="x")
        tk.Button(단추틀, text="인식하기 (Enter)", font=(한글글꼴, 11),
                  command=self.인식하기).pack(side="left", expand=True, fill="x", padx=(0, 4))
        tk.Button(단추틀, text="지우기 (C)", font=(한글글꼴, 11),
                  command=self.지우기).pack(side="left", expand=True, fill="x", padx=(4, 0))

        # --- 오른쪽: 결과 표시 영역 ---
        오른쪽틀 = tk.Frame(창, padx=12, pady=12)
        오른쪽틀.grid(row=0, column=1, sticky="n")

        tk.Label(오른쪽틀, text="인식 결과", font=(한글글꼴, 12)).pack()
        self.결과글자 = tk.Label(오른쪽틀, text="?", font=("Consolas", 88, "bold"), fg="#1565c0")
        self.결과글자.pack()
        self.확신도글자 = tk.Label(오른쪽틀, text="숫자를 써 보세요", font=(한글글꼴, 11))
        self.확신도글자.pack(pady=(0, 10))

        tk.Label(오른쪽틀, text="숫자별 확률", font=(한글글꼴, 11)).pack(anchor="w")
        self.확률막대 = []  # 0~9 각 숫자의 확률을 보여 주는 막대들
        for 숫자 in range(10):
            줄 = tk.Frame(오른쪽틀)
            줄.pack(anchor="w", pady=1)
            tk.Label(줄, text=str(숫자), font=("Consolas", 11), width=2).pack(side="left")
            막대 = tk.Canvas(줄, width=150, height=13, bg="#eeeeee", highlightthickness=0)
            막대.pack(side="left")
            막대칸 = 막대.create_rectangle(0, 0, 0, 13, fill="#1565c0", width=0)
            숫자글자 = tk.Label(줄, text="  0.0%", font=("Consolas", 9), width=7)
            숫자글자.pack(side="left")
            self.확률막대.append((막대, 막대칸, 숫자글자))

        # 화면에 보이는 그림과 똑같은 내용을 PIL 이미지에도 그려서 모델 입력으로 사용합니다.
        self.그림 = Image.new("L", (칠판크기, 칠판크기), color=255)
        self.그리기 = ImageDraw.Draw(self.그림)

        # 마우스와 키보드 이벤트 연결
        self.칠판.bind("<Button-1>", self.그리기_시작)
        self.칠판.bind("<B1-Motion>", self.그리는_중)
        self.칠판.bind("<ButtonRelease-1>", self.그리기_끝)
        창.bind("<Return>", lambda 이벤트: self.인식하기())
        창.bind("c", lambda 이벤트: self.지우기())
        창.bind("C", lambda 이벤트: self.지우기())

    # ----- 그리기 관련 -----
    def 그리기_시작(self, 이벤트):
        self.이전좌표 = (이벤트.x, 이벤트.y)
        # 점 하나만 찍어도 보이도록 작은 원을 그립니다.
        반지름 = 붓두께 // 2
        self.칠판.create_oval(이벤트.x - 반지름, 이벤트.y - 반지름,
                              이벤트.x + 반지름, 이벤트.y + 반지름,
                              fill="black", width=0)
        self.그리기.ellipse([이벤트.x - 반지름, 이벤트.y - 반지름,
                            이벤트.x + 반지름, 이벤트.y + 반지름], fill=0)

    def 그리는_중(self, 이벤트):
        if self.이전좌표 is None:
            self.이전좌표 = (이벤트.x, 이벤트.y)
            return
        현재좌표 = (이벤트.x, 이벤트.y)
        # 화면(Canvas)과 내부 이미지(PIL)에 같은 선을 그립니다.
        self.칠판.create_line(*self.이전좌표, *현재좌표, fill="black",
                              width=붓두께, capstyle=tk.ROUND, smooth=True)
        self.그리기.line([self.이전좌표, 현재좌표], fill=0, width=붓두께)
        self.이전좌표 = 현재좌표

    def 그리기_끝(self, 이벤트):
        self.이전좌표 = None
        self.인식하기()  # 손을 떼면 바로 인식

    def 지우기(self):
        self.칠판.delete("all")
        self.그리기.rectangle([0, 0, 칠판크기, 칠판크기], fill=255)
        self.결과글자.config(text="?")
        self.확신도글자.config(text="숫자를 써 보세요")
        for 막대, 막대칸, 숫자글자 in self.확률막대:
            막대.coords(막대칸, 0, 0, 0, 13)
            숫자글자.config(text="  0.0%")

    # ----- 인식 관련 -----
    def 인식하기(self):
        입력텐서, _ = MNIST_형식으로_변환(self.그림)
        if 입력텐서 is None:
            self.확신도글자.config(text="아직 아무것도 그리지 않았습니다")
            return

        with torch.no_grad():  # 추론이므로 기울기 계산을 끕니다.
            출력 = self.모델(입력텐서)
            확률 = F.softmax(출력, dim=1)[0]

        예측숫자 = int(확률.argmax().item())
        확신도 = float(확률[예측숫자].item()) * 100

        self.결과글자.config(text=str(예측숫자))
        self.확신도글자.config(text=f"확신도 {확신도:.1f}%")

        # 0~9 각 숫자의 확률을 막대그래프로 표시합니다.
        for 숫자, (막대, 막대칸, 숫자글자) in enumerate(self.확률막대):
            값 = float(확률[숫자].item())
            막대.coords(막대칸, 0, 0, 150 * 값, 13)
            막대.itemconfig(막대칸, fill="#1565c0" if 숫자 == 예측숫자 else "#90caf9")
            숫자글자.config(text=f"{값 * 100:5.1f}%")

        print(f"인식 결과: {예측숫자} (확신도 {확신도:.1f}%)")


def main():
    작업표시줄_아이콘_설정()  # 창을 만들기 전에 앱 식별자를 먼저 지정해야 합니다.
    모델 = 모델_불러오기()
    print("모델을 불러왔습니다. 창이 열리면 마우스로 숫자를 써 보세요.")
    창 = tk.Tk()
    작업표시줄_아이콘_설정(창)  # 창이 생긴 뒤 아이콘을 지정합니다.
    손글씨인식앱(창, 모델)
    창.mainloop()


if __name__ == "__main__":
    main()
