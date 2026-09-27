# 손글씨 숫자 인식기 (MNIST)

같은 CNN 모델을 **데스크톱 버전**과 **웹 버전** 두 가지로 제공합니다.

| 폴더 | 역할 | 기술 |
| --- | --- | --- |
| `desktop_version/` | **학습** + 로컬 인식. 가중치의 유일한 출처 | PyTorch · Tkinter |
| `web_version/` | **추론만**. GitHub Pages 정적 배포 | 순수 자바스크립트 (의존성 0개) |

설계 문서: `docs/superpowers/specs/2026-09-28-손글씨인식-웹-데스크톱-분리-design.md`

## ⚠️ 파이썬은 `py` 로 실행하세요

이 PC에는 파이썬이 두 개 있고 **`python` 에는 torch 가 없습니다.**

| 명령 | 실체 | torch |
| --- | --- | --- |
| `python` | Microsoft Store 스텁 | ❌ 없음 |
| `py` | `Python314\python.exe` | ✅ 있음 (torch 2.14, Pillow 12.3, torchvision 0.29) |

`python train.py` 는 `ModuleNotFoundError` 로 실패합니다. 항상 `py train.py` 를 쓰세요.

## 가중치가 흘러가는 길

```
desktop_version/train.py
        ↓ 학습
desktop_version/mnist_cnn.pt           (PyTorch state_dict, 4.8MB)
        ↓ py web_version/tools/가중치_내보내기.py
web_version/model/weights.bin + weights.json   (float32 덩어리 + 설명, 4.6MB)
        ↓ fetch
브라우저에서 순수 JS 추론
```

모델 구조를 바꾸면 **네 곳을 함께** 고쳐야 합니다.

1. `desktop_version/model.py` — 층 정의
2. `web_version/tools/가중치_내보내기.py` — `내보낼_순서`, `기대하는_모양`
3. `web_version/js/가중치.js` — `기대하는_모양`
4. `web_version/js/모델.js` — 순전파

그리고 `py train.py` 로 재학습 → `py tools/가중치_내보내기.py` → `py tools/고정표본_만들기.py`
순으로 다시 돌려야 합니다.

## 전처리는 양쪽이 반드시 같아야 합니다

`desktop_version/draw_predict.py` 의 `MNIST_형식으로_변환` 과
`web_version/js/전처리.js` 의 같은 이름 함수는 **단계·반올림까지 동일**해야 합니다.
**한쪽만 고치지 마세요.** 고쳤다면 고정표본을 다시 만들고 자가진단을 돌려야 합니다.

```bash
cd web_version
py tools/고정표본_만들기.py     # 데스크톱 코드를 호출해 기대값을 새로 만듦
py -m http.server 8000          # 그 뒤 http://localhost:8000/자가진단.html
```

현재 리샘플 결과는 PIL LANCZOS 와 **바이트 단위로 완전히 일치**합니다 (허용오차 없음).
자가진단은 `테스트/고정표본.json` 과 대조해 총 68건(7개 검사 모음)을 모두 통과합니다.

## 알려진 의도된 차이

PIL `ImageDraw.line` 은 계단식이고 캔버스 `stroke` 는 가장자리를 부드럽게 칠합니다.
사람이 같은 모양을 그려도 두 버전의 입력 화소는 가장자리에서 조금 다릅니다.
보장 범위는 **"픽셀 단위 동일"이 아니라 "같은 숫자를 예측"** 입니다.
실제로 데스크톱과 웹에 같은 캔버스 바이트를 넣으면 세 자리 숫자 모두 같은 예측이 나옴을 확인했습니다.

## 커밋하지 않는 것

`.gitignore` 로 `desktop_version/data/`(MNIST 64MB)와 `__pycache__/` 를 제외합니다.
`mnist_cnn.pt` 와 `weights.bin` 은 **커밋합니다** — 그래야 학습 없이 바로 쓸 수 있습니다.

## 배포

`main` 에 푸시하면 `.github/workflows/deploy.yml` 이 `web_version/` 만 Pages 로 올립니다.
저장소 설정에서 Settings → Pages → Source 를 "GitHub Actions" 로 한 번 바꿔 두어야 합니다.
