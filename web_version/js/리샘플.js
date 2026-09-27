/**
 * PIL(Pillow) 의 Image.resize(..., Image.LANCZOS) 를 자바스크립트로 재현합니다.
 *
 * 왜 브라우저의 drawImage 스케일링을 쓰지 않는가:
 *   브라우저마다 보간 방식이 달라 같은 입력에 같은 결과를 보장하지 못합니다.
 *   그러면 데스크톱 버전과의 일치를 테스트로 증명할 수 없습니다.
 *
 * PIL 과 같게 맞춘 것:
 *   - 가로 패스 → uint8 로 자름 → 세로 패스 (2단계 분리 필터)
 *   - 계수를 22비트 고정소수점 정수로 바꿔 누적 (PRECISION_BITS = 22)
 *   - 누적 전에 2^21 을 더해 반올림하고, 2^22 로 나눈 뒤 0~255 로 자름
 */

const 정밀도비트 = 22;
const 배수 = 1 << 정밀도비트;        // 4194304
const 반올림보정 = 1 << (정밀도비트 - 1);  // 2097152
const 지지반경 = 3.0;                 // Lanczos-3

/** sin(파이 x) / (파이 x). x 가 0 인 경우는 호출 전에 걸러집니다. */
function 싱크(x) {
  const 파이x = Math.PI * x;
  return Math.sin(파이x) / 파이x;
}

/** PIL 의 lanczos_filter 와 같은 창 함수입니다. */
function 란초스(x) {
  if (x < -지지반경 || x >= 지지반경) return 0.0;
  if (x === 0.0) return 1.0;
  return 싱크(x) * 싱크(x / 지지반경);
}

/**
 * 한 축에 대한 고정소수점 계수표를 만듭니다.
 * 돌려주는 값: { 계수(Int32Array), 시작(Int32Array), 길이(Int32Array), 폭 }
 *   출력 자리 xx 는 입력의 시작[xx] 부터 길이[xx] 개 화소를 계수 계수[xx*폭 + k] 로 섞습니다.
 */
function 계수표_만들기(입력크기, 출력크기) {
  const 배율 = 입력크기 / 출력크기;
  const 필터배율 = Math.max(1.0, 배율);   // 확대할 때는 1 로 고정됩니다
  const 지지폭 = 지지반경 * 필터배율;
  const 폭 = Math.ceil(지지폭) * 2 + 1;

  const 계수 = new Int32Array(출력크기 * 폭);
  const 시작 = new Int32Array(출력크기);
  const 길이 = new Int32Array(출력크기);
  const 임시 = new Float64Array(폭);

  for (let xx = 0; xx < 출력크기; xx++) {
    const 중심 = (xx + 0.5) * 배율;

    let 처음 = Math.floor(중심 - 지지폭);
    if (처음 < 0) 처음 = 0;
    let 끝 = Math.ceil(중심 + 지지폭);
    if (끝 > 입력크기) 끝 = 입력크기;
    const 개수 = 끝 - 처음;

    let 합 = 0.0;
    for (let k = 0; k < 개수; k++) {
      const 무게 = 란초스((k + 처음 - 중심 + 0.5) / 필터배율);
      임시[k] = 무게;
      합 += 무게;
    }
    if (합 !== 0.0) {
      for (let k = 0; k < 개수; k++) 임시[k] /= 합;
    }

    시작[xx] = 처음;
    길이[xx] = 개수;
    for (let k = 0; k < 개수; k++) {
      // PIL 의 normalize_coeffs_8bpc: 부호 방향으로 0.5 를 더한 뒤 잘라 냅니다.
      const 값 = 임시[k] * 배수;
      계수[xx * 폭 + k] = Math.trunc(값 + (값 < 0 ? -0.5 : 0.5));
    }
  }
  return { 계수, 시작, 길이, 폭 };
}

/** 22비트 고정소수점 누적값을 0~255 바이트로 되돌립니다. */
function 자르기(누적) {
  // 값이 2^31 을 넘을 수 있어 >> 대신 나눗셈을 씁니다.
  // 음수에서도 Math.floor 는 산술 우측 시프트와 같은 결과를 줍니다.
  const 값 = Math.floor(누적 / 배수);
  if (값 < 0) return 0;
  if (값 > 255) return 255;
  return 값;
}

/** 가로 방향으로만 크기를 바꿉니다. (입가로 × 세로) → (새가로 × 세로) */
function 가로_패스(입력, 입가로, 세로, 새가로) {
  const { 계수, 시작, 길이, 폭 } = 계수표_만들기(입가로, 새가로);
  const 출력 = new Uint8ClampedArray(새가로 * 세로);
  for (let y = 0; y < 세로; y++) {
    const 입줄 = y * 입가로;
    const 출줄 = y * 새가로;
    for (let xx = 0; xx < 새가로; xx++) {
      const 처음 = 시작[xx];
      const 개수 = 길이[xx];
      const 계수시작 = xx * 폭;
      let 누적 = 반올림보정;
      for (let k = 0; k < 개수; k++) {
        누적 += 입력[입줄 + 처음 + k] * 계수[계수시작 + k];
      }
      출력[출줄 + xx] = 자르기(누적);
    }
  }
  return 출력;
}

/** 세로 방향으로만 크기를 바꿉니다. (가로 × 입세로) → (가로 × 새세로) */
function 세로_패스(입력, 가로, 입세로, 새세로) {
  const { 계수, 시작, 길이, 폭 } = 계수표_만들기(입세로, 새세로);
  const 출력 = new Uint8ClampedArray(가로 * 새세로);
  for (let yy = 0; yy < 새세로; yy++) {
    const 처음 = 시작[yy];
    const 개수 = 길이[yy];
    const 계수시작 = yy * 폭;
    const 출줄 = yy * 가로;
    for (let x = 0; x < 가로; x++) {
      let 누적 = 반올림보정;
      for (let k = 0; k < 개수; k++) {
        누적 += 입력[(처음 + k) * 가로 + x] * 계수[계수시작 + k];
      }
      출력[출줄 + x] = 자르기(누적);
    }
  }
  return 출력;
}

/**
 * 회색조 이미지를 LANCZOS 로 다시 표본화합니다. 축소·확대 모두 됩니다.
 * 입력은 길이 입가로 × 입세로 의 바이트 배열(행 우선)입니다.
 */
export function 란초스_축소(입력, 입가로, 입세로, 새가로, 새세로) {
  let 현재 = 입력;
  let 현가로 = 입가로;

  // PIL 도 크기가 같은 축은 건너뜁니다. 돌려도 결과는 같지만 불필요한 계산입니다.
  if (새가로 !== 입가로) {
    현재 = 가로_패스(현재, 입가로, 입세로, 새가로);
    현가로 = 새가로;
  }
  if (새세로 !== 입세로) {
    현재 = 세로_패스(현재, 현가로, 입세로, 새세로);
  }

  // 두 축 모두 건너뛴 경우에도 항상 새 배열을 돌려줍니다(호출 쪽이 입력을 고치지 않도록).
  if (현재 === 입력) return Uint8ClampedArray.from(입력);
  return 현재;
}
