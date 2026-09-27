"""
데스크톱 버전이 학습한 가중치 파일(mnist_cnn.pt)을 웹 버전이 읽을 수 있는
`weights.bin` + `weights.json` 한 쌍으로 바꿔 줍니다.

특징:
    - 파이썬 표준 라이브러리만 사용합니다. (torch / numpy 설치가 필요 없습니다)
      .pt 파일은 사실 zip 압축 파일이며, 그 안에 텐서 목록(pickle)과
      실수 값 덩어리(data/0, data/1 ...)가 따로 들어 있습니다. 이 스크립트는
      그 구조를 직접 읽습니다.
    - 출력은 float32 리틀엔디언 값을 순서대로 이어 붙인 이진 파일 하나와,
      각 텐서의 이름·모양·시작 위치를 적은 JSON 파일 하나입니다.

실행 방법 (web_version 폴더에서):
    py tools/가중치_내보내기.py

    # 경로를 직접 지정하고 싶을 때
    py tools/가중치_내보내기.py --가중치 ../desktop_version/mnist_cnn.pt --출력 model
"""

import argparse
import collections
import json
import pickle
import struct
import sys
import zipfile
from pathlib import Path

# web_version/tools/ 기준 경로
도구폴더 = Path(__file__).resolve().parent
웹폴더 = 도구폴더.parent
기본_가중치파일 = 웹폴더.parent / "desktop_version" / "mnist_cnn.pt"
기본_출력폴더 = 웹폴더 / "model"

# 웹 버전 model.js 의 순전파 순서와 똑같은 순서로 내보냅니다.
# (이름은 desktop_version/model.py 의 층 이름 그대로입니다)
내보낼_순서 = [
    "합성곱1.weight",
    "합성곱1.bias",
    "합성곱2.weight",
    "합성곱2.bias",
    "완전연결1.weight",
    "완전연결1.bias",
    "완전연결2.weight",
    "완전연결2.bias",
]

# 층 이름 -> 기대하는 텐서 모양. 실제 파일과 다르면 바로 알려 주기 위한 검사표입니다.
기대하는_모양 = {
    "합성곱1.weight": [32, 1, 3, 3],
    "합성곱1.bias": [32],
    "합성곱2.weight": [64, 32, 3, 3],
    "합성곱2.bias": [64],
    "완전연결1.weight": [128, 9216],
    "완전연결1.bias": [128],
    "완전연결2.weight": [10, 128],
    "완전연결2.bias": [10],
}


class 텐서정보:
    """.pt 안의 한 텐서가 '어느 값 덩어리의 어디부터'인지를 담아 두는 그릇입니다."""

    def __init__(self, 저장소키: str, 시작: int, 모양, 보폭):
        self.저장소키 = 저장소키
        self.시작 = 시작
        self.모양 = list(모양)
        self.보폭 = list(보폭)

    @property
    def 개수(self) -> int:
        총 = 1
        for 길이 in self.모양:
            총 *= 길이
        return 총

    def 연속인가(self) -> bool:
        """값이 메모리에 C 순서(행 우선)로 빈틈없이 놓여 있는지 확인합니다."""
        기대보폭 = []
        누적 = 1
        for 길이 in reversed(self.모양):
            기대보폭.append(누적)
            누적 *= 길이
        기대보폭.reverse()
        return self.보폭 == 기대보폭


class _실수저장소:
    """pickle 안에 등장하는 torch.FloatStorage 자리를 대신 채우는 표시용 클래스입니다."""


def _텐서_다시만들기(저장소, 시작, 모양, 보폭, *나머지):
    """torch._utils._rebuild_tensor_v2 를 대신합니다. 실제 값은 읽지 않고 위치만 기억합니다."""
    del 나머지  # requires_grad, backward_hooks 등은 추론에 필요하지 않습니다.
    종류, 저장소키, 개수 = 저장소
    if 종류 != "float32":
        raise ValueError(f"float32 텐서만 지원합니다 (발견: {종류})")
    del 개수
    return 텐서정보(저장소키, 시작, 모양, 보폭)


class _가벼운_언피클러(pickle.Unpickler):
    """torch 없이도 state_dict 의 '구조'만 읽어 내는 최소한의 언피클러입니다."""

    def find_class(self, 모듈이름, 클래스이름):
        if (모듈이름, 클래스이름) == ("collections", "OrderedDict"):
            return collections.OrderedDict
        if 클래스이름 in ("_rebuild_tensor_v2", "_rebuild_tensor"):
            return _텐서_다시만들기
        if 클래스이름 in ("FloatStorage", "float32"):
            return _실수저장소
        raise pickle.UnpicklingError(
            f"예상하지 못한 항목이 들어 있습니다: {모듈이름}.{클래스이름}\n"
            "이 스크립트는 torch.save(모델.state_dict()) 로 저장한 파일만 읽습니다."
        )

    def persistent_load(self, 식별자):
        # torch 의 저장 형식: ('storage', 저장소클래스, 키, 장치, 원소개수)
        if not (isinstance(식별자, tuple) and 식별자 and 식별자[0] == "storage"):
            raise pickle.UnpicklingError(f"알 수 없는 저장소 참조: {식별자!r}")
        _, 저장소클래스, 키, _장치, 개수 = 식별자
        if 저장소클래스 is not _실수저장소:
            raise pickle.UnpicklingError("float32 이외의 자료형은 지원하지 않습니다.")
        return ("float32", str(키), int(개수))


def 상태사전_읽기(가중치파일: Path):
    """.pt(zip) 파일을 열어 (텐서정보 사전, 값 덩어리 읽기 함수) 를 돌려줍니다."""
    보관함 = zipfile.ZipFile(가중치파일)
    이름목록 = 보관함.namelist()

    피클이름 = next((이름 for 이름 in 이름목록 if 이름.endswith("data.pkl")), None)
    if 피클이름 is None:
        raise ValueError(
            "data.pkl 을 찾을 수 없습니다. 아주 오래된 형식(zip이 아닌 .pt)이라면 "
            "torch 가 설치된 환경에서 다시 저장해 주세요."
        )
    뿌리 = 피클이름[: -len("data.pkl")]  # 예: 'archive/'

    # 저장된 바이트 순서 확인 (보통 little)
    바이트순서 = "little"
    if 뿌리 + "byteorder" in 이름목록:
        바이트순서 = 보관함.read(뿌리 + "byteorder").decode().strip()
    if 바이트순서 != "little":
        raise ValueError(f"리틀엔디언 파일만 지원합니다 (발견: {바이트순서})")

    상태사전 = _가벼운_언피클러(zipfile.Path(보관함, 피클이름).open("rb")).load()

    def 값덩어리_읽기(저장소키: str) -> bytes:
        return 보관함.read(f"{뿌리}data/{저장소키}")

    return 상태사전, 값덩어리_읽기


def 내보내기(가중치파일: Path, 출력폴더: Path) -> None:
    if not 가중치파일.exists():
        print(f"[오류] 가중치 파일이 없습니다: {가중치파일}", file=sys.stderr)
        print("      먼저 desktop_version 에서 'py train.py' 를 실행해 주세요.", file=sys.stderr)
        sys.exit(1)

    상태사전, 값덩어리_읽기 = 상태사전_읽기(가중치파일)

    빠진층 = [이름 for 이름 in 내보낼_순서 if 이름 not in 상태사전]
    if 빠진층:
        print(f"[오류] 가중치 파일에 다음 층이 없습니다: {', '.join(빠진층)}", file=sys.stderr)
        print(f"      파일에 들어 있는 항목: {', '.join(상태사전)}", file=sys.stderr)
        sys.exit(1)

    출력폴더.mkdir(parents=True, exist_ok=True)
    이진파일 = 출력폴더 / "weights.bin"
    설명파일 = 출력폴더 / "weights.json"

    텐서설명 = []
    시작위치 = 0  # float32 개수 단위의 시작 위치

    with 이진파일.open("wb") as 출력:
        for 이름 in 내보낼_순서:
            정보: 텐서정보 = 상태사전[이름]
            if not isinstance(정보, 텐서정보):
                raise TypeError(f"'{이름}' 항목이 텐서가 아닙니다.")
            if 정보.모양 != 기대하는_모양[이름]:
                print(
                    f"[오류] '{이름}' 의 모양이 다릅니다. "
                    f"기대 {기대하는_모양[이름]}, 실제 {정보.모양}\n"
                    "      web_version/js/모델.js 의 구조도 함께 고쳐야 합니다.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if not 정보.연속인가():
                raise ValueError(f"'{이름}' 이(가) 연속 배치가 아닙니다. 지원하지 않습니다.")

            덩어리 = 값덩어리_읽기(정보.저장소키)
            처음바이트 = 정보.시작 * 4
            끝바이트 = 처음바이트 + 정보.개수 * 4
            if 끝바이트 > len(덩어리):
                raise ValueError(f"'{이름}' 의 값이 파일 범위를 벗어났습니다.")
            출력.write(덩어리[처음바이트:끝바이트])

            텐서설명.append({
                "이름": 이름,
                "모양": 정보.모양,
                "시작": 시작위치,
                "개수": 정보.개수,
            })
            시작위치 += 정보.개수
            print(f"  {이름:<20} 모양 {str(정보.모양):<18} 값 {정보.개수:>9,}개")

    설명 = {
        "형식": "mnist-cnn-float32-v1",
        "설명": "desktop_version/model.py 의 숫자인식CNN 가중치. 순서대로 이어 붙인 float32 값입니다.",
        "자료형": "float32",
        "바이트순서": "little",
        "이진파일": 이진파일.name,
        "전체개수": 시작위치,
        "정규화": {"평균": 0.1307, "표준편차": 0.3081},
        "텐서목록": 텐서설명,
    }
    설명파일.write_text(json.dumps(설명, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    크기MB = 이진파일.stat().st_size / (1024 * 1024)
    print()
    print(f"완료: {이진파일}  ({시작위치:,}개 값, {크기MB:.2f} MB)")
    print(f"완료: {설명파일}")

    # 값이 정상 범위인지 가볍게 확인합니다. (전부 0 이거나 NaN 이면 학습이 잘못된 파일입니다)
    첫값들 = struct.unpack_from("<8f", 이진파일.read_bytes(), 0)
    print(f"확인용 첫 8개 값: {', '.join(f'{값:+.4f}' for 값 in 첫값들)}")


def main():
    파서 = argparse.ArgumentParser(description="mnist_cnn.pt -> weights.bin/weights.json 변환")
    파서.add_argument("--가중치", type=Path, default=기본_가중치파일,
                      help=f"입력 .pt 파일 (기본값: {기본_가중치파일})")
    파서.add_argument("--출력", type=Path, default=기본_출력폴더,
                      help=f"출력 폴더 (기본값: {기본_출력폴더})")
    설정 = 파서.parse_args()
    내보내기(설정.가중치.resolve(), 설정.출력.resolve())


if __name__ == "__main__":
    main()
