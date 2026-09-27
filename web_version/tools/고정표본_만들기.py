"""
웹 버전 자가진단이 쓰는 고정표본(테스트/고정표본.json)을 만듭니다.

기대값은 전부 desktop_version 의 실제 코드를 호출해서 얻습니다.
(전처리는 draw_predict.MNIST_형식으로_변환, 추론은 model.숫자인식CNN)
그래야 "웹이 데스크톱과 같다"를 검증할 수 있습니다.

실행 방법 (web_version 폴더에서):
    py tools/고정표본_만들기.py
"""

import base64
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import datasets

도구폴더 = Path(__file__).resolve().parent
웹폴더 = 도구폴더.parent
데스크톱폴더 = 웹폴더.parent / "desktop_version"
출력파일 = 웹폴더 / "테스트" / "고정표본.json"

# 데스크톱 코드를 그대로 불러다 씁니다.
sys.path.insert(0, str(데스크톱폴더))
from model import 숫자인식CNN                      # noqa: E402
from draw_predict import MNIST_형식으로_변환        # noqa: E402

모사크기 = 112   # MNIST 28x28 을 4배로 키워 '그림판에 쓴 그림'을 흉내 냅니다.
모델표본수 = 20
전처리표본수 = 5


def 바이트_b64(배열, 자료형) -> str:
    """넘파이 배열을 지정한 자료형의 리틀엔디언 바이트로 만들어 base64 문자열로 돌려줍니다."""
    조밀 = np.ascontiguousarray(배열, dtype=자료형)
    return base64.b64encode(조밀.tobytes()).decode("ascii")


def 리샘플_표본():
    """란초스_축소 단위 검사용. 축소·확대·비정사각·1픽셀을 모두 포함합니다."""
    경우들 = [
        ("축소_정사각", (np.arange(16, dtype=np.uint8).reshape(4, 4) * 16), (2, 2)),
        ("확대_정사각", np.array([[0, 255], [255, 0]], dtype=np.uint8), (5, 5)),
        ("축소_가로긴", (np.arange(24, dtype=np.uint8).reshape(3, 8) * 10), (3, 2)),
        ("점하나_확대", np.array([[200]], dtype=np.uint8), (3, 3)),
        ("축소_세로긴", (np.arange(24, dtype=np.uint8).reshape(8, 3) * 10), (2, 3)),
    ]
    표본들 = []
    for 이름, 입력, (새가로, 새세로) in 경우들:
        결과 = np.array(Image.fromarray(입력, "L").resize((새가로, 새세로), Image.LANCZOS))
        표본들.append({
            "이름": 이름,
            "입가로": int(입력.shape[1]), "입세로": int(입력.shape[0]),
            "입력": 바이트_b64(입력, np.uint8),
            "새가로": 새가로, "새세로": 새세로,
            "기대": 바이트_b64(결과, np.uint8),
        })
        print(f"  리샘플 {이름:<12} {입력.shape[1]}x{입력.shape[0]} -> {새가로}x{새세로}")
    return 표본들


def 중간값_기록(그림: Image.Image):
    """
    실패했을 때 어느 단계에서 갈렸는지 보이게 하려고 중간 수치를 따로 계산합니다.
    통과 판정에는 쓰이지 않습니다. 판정 기준은 MNIST_형식으로_변환 의 실제 결과입니다.
    """
    반전 = Image.eval(그림.convert("L"), lambda 밝기: 255 - 밝기)
    글씨영역 = 반전.getbbox()
    if 글씨영역 is None:
        return None
    잘라낸 = 반전.crop(글씨영역)
    가로, 세로 = 잘라낸.size
    비율 = 20.0 / max(가로, 세로)
    새가로 = max(1, int(round(가로 * 비율)))
    새세로 = max(1, int(round(세로 * 비율)))
    도화지 = Image.new("L", (28, 28), color=0)
    도화지.paste(잘라낸.resize((새가로, 새세로), Image.LANCZOS),
                 ((28 - 새가로) // 2, (28 - 새세로) // 2))
    배열 = np.array(도화지, dtype=np.float32)
    총밝기 = 배열.sum()
    중심x = 중심y = 이동x = 이동y = 0.0
    if 총밝기 > 0:
        y좌표, x좌표 = np.nonzero(배열)
        가중치 = 배열[y좌표, x좌표]
        중심x = float((x좌표 * 가중치).sum() / 총밝기)
        중심y = float((y좌표 * 가중치).sum() / 총밝기)
        이동x = int(round(13.5 - 중심x))
        이동y = int(round(13.5 - 중심y))
    return {
        "글씨영역": [int(값) for 값 in 글씨영역],
        "잘가로": int(가로), "잘세로": int(세로),
        "새가로": int(새가로), "새세로": int(새세로),
        "중심x": 중심x, "중심y": 중심y,
        "이동x": int(이동x), "이동y": int(이동y),
    }


def 그림판_모사(mnist그림: Image.Image) -> Image.Image:
    """MNIST(검은 배경·흰 글씨) 28x28 을 그림판(흰 배경·검은 글씨) 112x112 로 바꿉니다."""
    큰그림 = mnist그림.resize((모사크기, 모사크기), Image.NEAREST)
    return Image.eval(큰그림, lambda 밝기: 255 - 밝기)


def 합성_표본들():
    """스펙의 Review Focus 가 지목한 극단 입력들. 흰 배경(255)에 검은 획을 긋습니다."""
    빈그림 = Image.new("L", (모사크기, 모사크기), color=255)

    가는세로선 = Image.new("L", (모사크기, 모사크기), color=255)
    화소 = 가는세로선.load()
    for y in range(36, 76):          # 세로 40, 가로 1 -> round(1 * 0.5) = 0 (은행가 반올림)
        화소[56, y] = 0

    점하나 = Image.new("L", (모사크기, 모사크기), color=255)
    점하나.load()[56, 56] = 0

    return [("빈그림", 빈그림), ("가는세로선", 가는세로선), ("점하나", 점하나)]


def 전처리_표본(모델, 평가데이터):
    표본들 = []
    대상 = [(f"mnist_{번호}", 그림판_모사(평가데이터[번호][0])) for 번호 in range(전처리표본수)]
    대상 += 합성_표본들()

    for 이름, 그림 in 대상:
        입력텐서, 배열 = MNIST_형식으로_변환(그림)
        항목 = {
            "이름": 이름,
            "가로": 그림.size[0], "세로": 그림.size[1],
            "입력": 바이트_b64(np.array(그림.convert("L")), np.uint8),
            "기대없음": 입력텐서 is None,
        }
        if 입력텐서 is not None:
            with torch.no_grad():
                숫자 = int(모델(입력텐서).argmax(dim=1).item())
            항목["기대28"] = 바이트_b64(배열, np.uint8)
            항목["기대숫자"] = 숫자
            항목["중간"] = 중간값_기록(그림)
        표본들.append(항목)
        print(f"  전처리 {이름:<12} 빈그림={항목['기대없음']}")
    return 표본들


def 모델_표본(모델, 평가데이터):
    표본들 = []
    for 번호 in range(모델표본수):
        그림, _정답 = 평가데이터[번호]
        배열 = np.array(그림, dtype=np.float32)
        정규화 = (배열 / 255.0 - 0.1307) / 0.3081
        텐서 = torch.from_numpy(정규화).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            로짓 = 모델(텐서)[0]
        표본들.append({
            "이름": f"평가_{번호}",
            "입력": 바이트_b64(정규화, np.float32),
            "기대로짓": [float(값) for 값 in 로짓],
            "기대숫자": int(로짓.argmax().item()),
        })
    print(f"  모델   {모델표본수}개")
    return 표본들


def main():
    가중치파일 = 데스크톱폴더 / "mnist_cnn.pt"
    if not 가중치파일.exists():
        print(f"[오류] 가중치가 없습니다: {가중치파일}", file=sys.stderr)
        print("      desktop_version 에서 'py train.py' 를 먼저 실행해 주세요.", file=sys.stderr)
        sys.exit(1)

    모델 = 숫자인식CNN()
    모델.load_state_dict(torch.load(가중치파일, map_location="cpu"))
    모델.eval()

    평가데이터 = datasets.MNIST(root=str(데스크톱폴더 / "data"), train=False, download=False)

    print("고정표본을 만듭니다...")
    고정표본 = {
        "형식": "손글씨인식-고정표본-v1",
        "만든날짜": "2026-09-28",
        "정규화": {"평균": 0.1307, "표준편차": 0.3081},
        "리샘플": 리샘플_표본(),
        "전처리": 전처리_표본(모델, 평가데이터),
        "모델": 모델_표본(모델, 평가데이터),
    }

    출력파일.parent.mkdir(parents=True, exist_ok=True)
    출력파일.write_text(json.dumps(고정표본, ensure_ascii=False), encoding="utf-8")
    크기KB = 출력파일.stat().st_size / 1024
    print(f"\n완료: {출력파일}  ({크기KB:.0f} KB)")


if __name__ == "__main__":
    main()
