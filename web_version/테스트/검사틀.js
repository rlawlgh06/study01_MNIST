/**
 * 외부 라이브러리 없이 쓰는 초소형 검사 도구입니다.
 * 브라우저와 Node 어디서든 돌도록 DOM 을 건드리지 않습니다.
 */

/** 검사 여러 개를 모아 순서대로 실행합니다. */
export function 검사_모음(이름) {
  const 항목들 = [];
  return {
    이름,
    검사(설명, 함수) {
      항목들.push({ 설명, 함수 });
    },
    async 실행() {
      const 결과 = [];
      for (const { 설명, 함수 } of 항목들) {
        const 시작 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
        try {
          await 함수();
          결과.push({ 설명, 통과: true, 메시지: '', 밀리초: 소수두자리(시작) });
        } catch (오류) {
          결과.push({ 설명, 통과: false, 메시지: 오류.message, 밀리초: 소수두자리(시작) });
        }
      }
      return { 이름, 결과 };
    },
  };
}

function 소수두자리(시작) {
  const 지금 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
  return Math.round((지금 - 시작) * 100) / 100;
}

/** 두 값이 같은지 확인합니다. */
export function 같음_확인(실제, 기대, 설명) {
  if (실제 !== 기대) {
    throw new Error(`${설명}: 기대 ${기대}, 실제 ${실제}`);
  }
}

/** 정수 배열이 완전히 같은지 확인합니다. 어긋나면 처음 어긋난 자리를 알려 줍니다. */
export function 바이트배열_같음_확인(실제, 기대, 설명) {
  if (실제.length !== 기대.length) {
    throw new Error(`${설명}: 길이가 다릅니다. 기대 ${기대.length}, 실제 ${실제.length}`);
  }
  let 어긋난개수 = 0;
  let 첫자리 = -1;
  for (let i = 0; i < 기대.length; i++) {
    if (실제[i] !== 기대[i]) {
      어긋난개수 += 1;
      if (첫자리 < 0) 첫자리 = i;
    }
  }
  if (어긋난개수 > 0) {
    throw new Error(
      `${설명}: ${어긋난개수}/${기대.length}개 어긋남. ` +
      `색인 ${첫자리}에서 기대 ${기대[첫자리]}, 실제 ${실제[첫자리]}`);
  }
}

/** 실수 배열이 허용오차 안에서 같은지 확인하고, 최대 절대 오차를 돌려줍니다. */
export function 실수배열_근사_확인(실제, 기대, 허용오차, 설명) {
  if (실제.length !== 기대.length) {
    throw new Error(`${설명}: 길이가 다릅니다. 기대 ${기대.length}, 실제 ${실제.length}`);
  }
  let 최대오차 = 0;
  let 최대자리 = -1;
  for (let i = 0; i < 기대.length; i++) {
    const 오차 = Math.abs(실제[i] - 기대[i]);
    if (오차 > 최대오차) {
      최대오차 = 오차;
      최대자리 = i;
    }
  }
  if (최대오차 > 허용오차) {
    throw new Error(
      `${설명}: 최대 오차 ${최대오차.toExponential(3)} > 허용 ${허용오차.toExponential(3)} ` +
      `(색인 ${최대자리}: 기대 ${기대[최대자리]}, 실제 ${실제[최대자리]})`);
  }
  return 최대오차;
}

/** base64 문자열을 바이트 배열로 되돌립니다. */
export function base64_바이트(문자열) {
  const 원시 = atob(문자열);
  const 결과 = new Uint8Array(원시.length);
  for (let i = 0; i < 원시.length; i++) 결과[i] = 원시.charCodeAt(i);
  return 결과;
}

/** base64 문자열을 float32 배열(리틀엔디언)로 되돌립니다. */
export function base64_실수(문자열) {
  const 바이트 = base64_바이트(문자열);
  return new Float32Array(바이트.buffer, 바이트.byteOffset, 바이트.byteLength / 4);
}
