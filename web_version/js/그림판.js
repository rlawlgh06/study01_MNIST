/**
 * 마우스 · 손가락 · 펜으로 숫자를 쓰는 그림판입니다.
 *
 * 캔버스를 두 장 씁니다. 데스크톱 버전이 화면용 Tkinter Canvas 와 모델 입력용 PIL 이미지를
 * 나란히 그리는 것과 같은 구조입니다.
 *   화면용 — 화면 배율(devicePixelRatio)만큼 키워 고해상도에서도 선명하게
 *   모델용 — 280×280 고정. 데스크톱과 같은 기하를 유지해야 예측이 갈리지 않습니다.
 */

export const 칠판크기 = 280;
export const 붓두께 = 20;

/** 캔버스 한 장을 흰 배경으로 초기화하고 붓 설정을 맞춥니다. */
function 맥락_준비(맥락) {
  // 캔버스 기본값은 '투명'이고 투명 화소의 RGB 는 0 입니다.
  // 흰색으로 채우지 않으면 배경이 검은색으로 읽혀 전처리가 통째로 뒤집힙니다.
  맥락.fillStyle = '#ffffff';
  맥락.fillRect(0, 0, 칠판크기, 칠판크기);
  맥락.strokeStyle = '#000000';
  맥락.fillStyle = '#000000';
  맥락.lineWidth = 붓두께;
  맥락.lineCap = 'round';
  맥락.lineJoin = 'round';
}

/**
 * 그림판을 만듭니다.
 *   화면캔버스 - 사용자에게 보이는 <canvas>
 *   모델캔버스 - 화면에 보이지 않아도 되는 280×280 <canvas>
 *   그리기끝나면 - 손을 뗐을 때 부를 함수 (없으면 아무것도 하지 않습니다)
 */
export function 그림판_만들기(화면캔버스, 모델캔버스, { 그리기끝나면 } = {}) {
  const 배율 = (typeof devicePixelRatio === 'number' && devicePixelRatio > 0)
    ? devicePixelRatio : 1;

  화면캔버스.width = Math.round(칠판크기 * 배율);
  화면캔버스.height = Math.round(칠판크기 * 배율);
  모델캔버스.width = 칠판크기;
  모델캔버스.height = 칠판크기;

  const 화면맥락 = 화면캔버스.getContext('2d');
  const 모델맥락 = 모델캔버스.getContext('2d', { willReadFrequently: true });
  화면맥락.scale(배율, 배율);   // 이제 두 맥락 모두 280 좌표계로 그립니다.

  let 그린적있나 = false;
  let 이전점 = null;
  let 활성포인터 = null;   // 지금 획을 그리고 있는 포인터의 id. 다른 손가락 입력은 무시합니다.

  function 지우기() {
    맥락_준비(화면맥락);
    맥락_준비(모델맥락);
    그린적있나 = false;
    이전점 = null;
    활성포인터 = null;
  }

  /** 두 맥락에 같은 점을 찍습니다. 점 하나만 눌러도 보이게 원을 그립니다. */
  function 점_찍기(x, y) {
    for (const 맥락 of [화면맥락, 모델맥락]) {
      맥락.beginPath();
      맥락.arc(x, y, 붓두께 / 2, 0, Math.PI * 2);
      맥락.fill();
    }
    그린적있나 = true;
  }

  /** 두 맥락에 같은 선분을 긋습니다. */
  function 선분_긋기(시작, 끝) {
    for (const 맥락 of [화면맥락, 모델맥락]) {
      맥락.beginPath();
      맥락.moveTo(시작[0], 시작[1]);
      맥락.lineTo(끝[0], 끝[1]);
      맥락.stroke();
    }
    그린적있나 = true;
  }

  /**
   * 점 목록을 이어서 한 획을 긋습니다.
   * 포인터 처리와 검사가 같은 길을 쓰도록 공개해 둡니다.
   */
  function 선_그리기(점들) {
    if (점들.length === 0) return;
    점_찍기(점들[0][0], 점들[0][1]);
    for (let i = 1; i < 점들.length; i++) 선분_긋기(점들[i - 1], 점들[i]);
  }

  /** 모델용 캔버스를 회색조 바이트로 읽습니다. 붓이 순수 검정이라 R 채널이면 충분합니다. */
  function 회색조_가져오기() {
    const 화소 = 모델맥락.getImageData(0, 0, 칠판크기, 칠판크기).data;
    const 회색조 = new Uint8ClampedArray(칠판크기 * 칠판크기);
    for (let i = 0; i < 회색조.length; i++) 회색조[i] = 화소[i * 4];
    return 회색조;
  }

  function 비었나() {
    return !그린적있나;
  }

  // ----- 포인터 입력 -----
  function 좌표(사건) {
    const 사각형 = 화면캔버스.getBoundingClientRect();
    // 화면에서 CSS 로 줄이거나 늘렸을 수 있으므로 280 좌표계로 되돌립니다.
    return [
      (사건.clientX - 사각형.left) * (칠판크기 / 사각형.width),
      (사건.clientY - 사각형.top) * (칠판크기 / 사각형.height),
    ];
  }

  화면캔버스.addEventListener('pointerdown', (사건) => {
    // 이미 다른 손가락으로 획을 긋는 중이면 새 포인터는 무시합니다. (두 손가락 = 선 뒤엉킴)
    if (활성포인터 !== null) return;
    // 보조 포인터(멀티터치의 두 번째 이후)와 마우스 오른쪽 버튼은 그리기가 아닙니다.
    if (!사건.isPrimary || 사건.button !== 0) return;
    사건.preventDefault();
    화면캔버스.setPointerCapture(사건.pointerId);
    활성포인터 = 사건.pointerId;
    이전점 = 좌표(사건);
    점_찍기(이전점[0], 이전점[1]);
  });

  화면캔버스.addEventListener('pointermove', (사건) => {
    if (이전점 === null || 사건.pointerId !== 활성포인터) return;
    사건.preventDefault();
    const 지금 = 좌표(사건);
    선분_긋기(이전점, 지금);
    이전점 = 지금;
  });

  function 그리기_끝(사건) {
    if (사건.pointerId !== 활성포인터) return;
    이전점 = null;
    활성포인터 = null;
    if (화면캔버스.hasPointerCapture(사건.pointerId)) {
      화면캔버스.releasePointerCapture(사건.pointerId);
    }
    if (그리기끝나면) 그리기끝나면();
  }

  화면캔버스.addEventListener('pointerup', 그리기_끝);
  화면캔버스.addEventListener('pointercancel', 그리기_끝);

  지우기();
  return { 지우기, 회색조_가져오기, 선_그리기, 비었나 };
}
