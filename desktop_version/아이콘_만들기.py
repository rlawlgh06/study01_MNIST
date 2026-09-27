"""
바탕 화면 바로가기와 작업 표시줄에 쓸 아이콘 파일(아이콘.ico)을 만듭니다.
Pillow로 직접 그리므로 별도의 이미지 파일이 필요하지 않습니다.

실행 방법:
    python 아이콘_만들기.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

현재폴더 = Path(__file__).resolve().parent
아이콘파일 = 현재폴더 / "아이콘.ico"

기본크기 = 256              # 큰 크기로 그린 뒤 여러 크기로 줄여 저장합니다.
배경색 = (21, 101, 192)     # 앱에서 쓰는 파란색 (#1565c0)
글씨색 = (255, 255, 255)


def 글꼴_찾기(크기: int):
    """숫자를 그릴 굵은 글꼴을 순서대로 찾아 돌려줍니다."""
    후보들 = [
        r"C:\Windows\Fonts\segoeuib.ttf",   # Segoe UI Bold
        r"C:\Windows\Fonts\arialbd.ttf",    # Arial Bold
        r"C:\Windows\Fonts\malgunbd.ttf",   # 맑은 고딕 Bold
    ]
    for 경로 in 후보들:
        if Path(경로).exists():
            return ImageFont.truetype(경로, 크기)
    return ImageFont.load_default()


def 아이콘_그리기() -> Image.Image:
    """모서리가 둥근 파란 사각형 위에 흰 숫자 '7'을 얹은 아이콘을 그립니다."""
    그림 = Image.new("RGBA", (기본크기, 기본크기), (0, 0, 0, 0))
    그리기 = ImageDraw.Draw(그림)

    # 둥근 사각형 배경
    여백 = 10
    그리기.rounded_rectangle(
        [여백, 여백, 기본크기 - 여백, 기본크기 - 여백],
        radius=48, fill=배경색,
    )

    # 가운데에 숫자 '7' (손글씨 숫자 인식을 나타냄)
    글꼴 = 글꼴_찾기(170)
    숫자 = "7"
    왼쪽, 위쪽, 오른쪽, 아래쪽 = 그리기.textbbox((0, 0), 숫자, font=글꼴)
    x = (기본크기 - (오른쪽 - 왼쪽)) // 2 - 왼쪽
    y = (기본크기 - (아래쪽 - 위쪽)) // 2 - 위쪽 - 8
    그리기.text((x, y), 숫자, font=글꼴, fill=글씨색)

    # 아래쪽에 밑줄(공책 줄) 한 개를 그려 '손글씨' 느낌을 더합니다.
    그리기.rounded_rectangle(
        [72, 196, 기본크기 - 72, 206], radius=5, fill=(255, 255, 255, 150),
    )
    return 그림


def main():
    아이콘 = 아이콘_그리기()
    # 윈도우가 상황에 맞는 크기를 골라 쓸 수 있도록 여러 해상도를 한 파일에 담습니다.
    크기목록 = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    아이콘.save(아이콘파일, format="ICO", sizes=크기목록)
    print(f"아이콘을 만들었습니다: {아이콘파일}")


if __name__ == "__main__":
    main()
