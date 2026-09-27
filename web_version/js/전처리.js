/**
 * 그림판에 그린 그림을 MNIST 학습 데이터와 같은 형식(28×28)으로 바꿉니다.
 *
 * desktop_version/draw_predict.py 의 MNIST_형식으로_변환 과 단계·반올림까지
 * 같아야 합니다. 한쪽만 고치면 두 버전의 예측이 갈립니다.
 *
 * 입력은 '흰 배경(255) · 검은 글씨(0)' 회색조 바이트 배열입니다.
 * 캔버스에서 읽어 올 때 흰색으로 먼저 채워야 한다는 점은 그림판.js 가 책임집니다.
 */
import { 란초스_축소 } from './리샘플.js';

const 평균 = 0.1307;
const 표준편차 = 0.3081;
const 목표크기 = 28;
const 글씨크기 = 20;   // MNIST 는 숫자를 20×20 안에 넣습니다

/**
 * 파이썬 round() 와 같은 '은행가 반올림'입니다.
 * 정확히 .5 인 값은 가까운 짝수로 갑니다. JS 의 Math.round 는 항상 위로 올리므로
 * 그대로 쓰면 round(12.5) 가 13 이 되어 데스크톱과 크기가 1픽셀 어긋납니다.
 */
export function 파이썬_반올림(값) {
  const 내림 = Math.floor(값);
  const 나머지 = 값 - 내림;
  if (나머지 > 0.5) return 내림 + 1;
  if (나머지 < 0.5) return 내림;
  return 내림 % 2 === 0 ? 내림 : 내림 + 1;
}

/**
 * 회색조 바이트 배열을 모델 입력으로 바꿉니다.
 * 아무것도 그리지 않았으면 null 을 돌려줍니다.
 */
export function MNIST_형식으로_변환(회색조, 가로, 세로) {
  // 1. 반전 — 그림판은 흰 배경·검은 글씨, MNIST 는 검은 배경·흰 글씨입니다.
  const 반전 = new Uint8ClampedArray(가로 * 세로);
  for (let i = 0; i < 반전.length; i++) 반전[i] = 255 - 회색조[i];

  // 2. 글씨영역 찾기 — PIL getbbox() 와 같이 0 이 아닌 화소의 최소 사각형입니다.
  let 최소x = 가로;
  let 최소y = 세로;
  let 최대x = -1;
  let 최대y = -1;
  for (let y = 0; y < 세로; y++) {
    const 줄 = y * 가로;
    for (let x = 0; x < 가로; x++) {
      if (반전[줄 + x] !== 0) {
        if (x < 최소x) 최소x = x;
        if (x > 최대x) 최대x = x;
        if (y < 최소y) 최소y = y;
        if (y > 최대y) 최대y = y;
      }
    }
  }
  if (최대x < 0) return null;   // 아무것도 그리지 않음

  // 3. 자르기
  const 잘가로 = 최대x - 최소x + 1;
  const 잘세로 = 최대y - 최소y + 1;
  const 잘라낸 = new Uint8ClampedArray(잘가로 * 잘세로);
  for (let y = 0; y < 잘세로; y++) {
    const 원줄 = (y + 최소y) * 가로 + 최소x;
    const 새줄 = y * 잘가로;
    for (let x = 0; x < 잘가로; x++) 잘라낸[새줄 + x] = 반전[원줄 + x];
  }

  // 4. 긴 변이 20 이 되도록 비율을 지키며 크기를 바꿉니다.
  //    아주 가는 획이면 반올림 결과가 0 이 될 수 있어 최소 1 로 올립니다.
  const 비율 = 글씨크기 / Math.max(잘가로, 잘세로);
  const 새가로 = Math.max(1, 파이썬_반올림(잘가로 * 비율));
  const 새세로 = Math.max(1, 파이썬_반올림(잘세로 * 비율));
  const 축소 = 란초스_축소(잘라낸, 잘가로, 잘세로, 새가로, 새세로);

  // 5. 28×28 검은 도화지 가운데에 붙입니다.
  const 도화지 = new Uint8ClampedArray(목표크기 * 목표크기);
  const 시작x = Math.floor((목표크기 - 새가로) / 2);
  const 시작y = Math.floor((목표크기 - 새세로) / 2);
  for (let y = 0; y < 새세로; y++) {
    const 원줄 = y * 새가로;
    const 새줄 = (y + 시작y) * 목표크기 + 시작x;
    for (let x = 0; x < 새가로; x++) 도화지[새줄 + x] = 축소[원줄 + x];
  }

  // 6. 무게중심을 (13.5, 13.5) 로 옮깁니다. 중간값은 데스크톱과 같이 uint8 로 둡니다.
  const 정렬 = 무게중심_정렬(도화지);

  // 7. 정규화
  const 정규화배열 = new Float32Array(목표크기 * 목표크기);
  for (let i = 0; i < 정규화배열.length; i++) {
    정규화배열[i] = (정렬[i] / 255 - 평균) / 표준편차;
  }

  return { 정규화배열, 미리보기: 정렬 };
}

/** 픽셀 밝기를 가중치로 무게중심을 구해 정수 픽셀만큼 평행이동합니다. */
function 무게중심_정렬(도화지) {
  let 총밝기 = 0;
  let 가중x = 0;
  let 가중y = 0;
  for (let y = 0; y < 목표크기; y++) {
    const 줄 = y * 목표크기;
    for (let x = 0; x < 목표크기; x++) {
      const 값 = 도화지[줄 + x];
      if (값 !== 0) {
        총밝기 += 값;
        가중x += x * 값;
        가중y += y * 값;
      }
    }
  }
  if (총밝기 <= 0) return 도화지;

  const 이동x = 파이썬_반올림(13.5 - 가중x / 총밝기);
  const 이동y = 파이썬_반올림(13.5 - 가중y / 총밝기);
  if (이동x === 0 && 이동y === 0) return 도화지;

  // 출력(x, y) = 입력(x - 이동x, y - 이동y), 범위를 벗어나면 0.
  // PIL 의 Image.AFFINE (1, 0, -이동x, 0, 1, -이동y) + NEAREST 와 같습니다.
  const 결과 = new Uint8ClampedArray(목표크기 * 목표크기);
  for (let y = 0; y < 목표크기; y++) {
    const 원y = y - 이동y;
    if (원y < 0 || 원y >= 목표크기) continue;
    const 원줄 = 원y * 목표크기;
    const 새줄 = y * 목표크기;
    for (let x = 0; x < 목표크기; x++) {
      const 원x = x - 이동x;
      if (원x < 0 || 원x >= 목표크기) continue;
      결과[새줄 + x] = 도화지[원줄 + 원x];
    }
  }
  return 결과;
}
