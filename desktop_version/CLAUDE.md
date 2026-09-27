# desktop_version — 학습과 로컬 인식

PyTorch 로 MNIST CNN 을 학습하고, Tkinter 그림판으로 손글씨를 인식합니다.
**이 폴더가 모델 가중치의 유일한 출처입니다.** 웹 버전은 여기서 나온 가중치만 씁니다.

상위 규칙은 `../CLAUDE.md` 를 먼저 보세요.

## 실행

**`python` 이 아니라 `py` 를 씁니다** (`python` 은 torch 가 없는 Store 스텁입니다).

```bash
py train.py              # 3 에폭 학습 → mnist_cnn.pt
py train.py --에폭 5     # 에폭 바꾸기
py draw_predict.py       # 그림판 실행
```

## 파일

| 파일 | 역할 |
| --- | --- |
| `model.py` | `숫자인식CNN` 구조 (합성곱 2 + 완전연결 2) |
| `train.py` | 학습하고 `mnist_cnn.pt` 저장 |
| `draw_predict.py` | Tkinter 그림판 + 인식. `MNIST_형식으로_변환` 이 여기 있습니다 |
| `아이콘_만들기.py`, `바로가기_만들기.ps1` | 바탕화면 · 시작 메뉴 바로가기 |
| `data/` | MNIST 자동 내려받기 (gitignore) |

## 코드 관례

- **한글 식별자**와 설명 주석을 씁니다 (`숫자인식CNN`, `합성곱1`, `칠판크기`).
  기존 코드 스타일이므로 새 코드도 맞춰 주세요.
- 경로는 `Path(__file__).resolve().parent` 기준으로 잡아, 어느 폴더에서 실행해도 같게 합니다.
- 추론할 때는 `모델.eval()` 과 `torch.no_grad()` 를 반드시 켭니다.

## 고칠 때 함께 봐야 하는 것

### `model.py` 의 층 구조를 바꾸면

웹 버전이 같은 구조를 전제하고 있습니다. 다음을 함께 고쳐야 합니다.

- `../web_version/tools/가중치_내보내기.py` 의 `내보낼_순서`, `기대하는_모양`
- `../web_version/js/가중치.js` 의 `기대하는_모양`
- `../web_version/js/모델.js` 의 `순전파`

그 뒤 `py train.py` → `py ../web_version/tools/가중치_내보내기.py` →
`py ../web_version/tools/고정표본_만들기.py` 순으로 다시 돌립니다.

### `draw_predict.py` 의 `MNIST_형식으로_변환` 을 바꾸면

`../web_version/js/전처리.js` 를 **같이** 고쳐야 합니다. 두 함수가 갈리면
같은 그림에 다른 숫자를 답하게 됩니다. 고친 뒤에는 반드시:

```bash
cd ../web_version
py tools/고정표본_만들기.py
py -m http.server 8000      # http://localhost:8000/자가진단.html 이 전부 통과해야 함
```

`고정표본_만들기.py` 는 이 폴더의 함수를 **직접 불러다** 기대값을 만듭니다.
그래서 여기를 고치면 고정표본이 저절로 따라오고, 웹 구현이 뒤처졌다면 검사가 실패합니다.
