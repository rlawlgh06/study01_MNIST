/**
 * 데스크톱이 학습한 가중치(weights.bin + weights.json)를 읽어 텐서 사전을 만듭니다.
 *
 * weights.bin 은 float32 리틀엔디언 값을 순서대로 이어 붙인 덩어리이고,
 * weights.json 이 각 텐서의 이름·모양·시작 위치를 알려 줍니다.
 * (만드는 쪽: web_version/tools/가중치_내보내기.py)
 */

/** 모델.js 의 순전파가 전제하는 텐서 모양입니다. 파일이 이와 다르면 바로 알려 줍니다. */
export const 기대하는_모양 = {
  '합성곱1.weight': [32, 1, 3, 3],
  '합성곱1.bias': [32],
  '합성곱2.weight': [64, 32, 3, 3],
  '합성곱2.bias': [64],
  '완전연결1.weight': [128, 9216],
  '완전연결1.bias': [128],
  '완전연결2.weight': [10, 128],
  '완전연결2.bias': [10],
};

/** 무엇이 잘못됐고 어떻게 고치는지를 함께 담는 오류입니다. */
export class 가중치오류 extends Error {
  constructor(메시지, 안내) {
    super(메시지);
    this.name = '가중치오류';
    this.안내 = 안내;
  }
}

const 내보내기_안내 =
  'web_version 폴더에서 다음을 실행해 가중치를 다시 내보내 주세요:\n' +
  '    py tools/가중치_내보내기.py';

async function 받아오기(주소) {
  let 응답;
  try {
    응답 = await fetch(주소);
  } catch (원인) {
    if (typeof location !== 'undefined' && location.protocol === 'file:') {
      throw new 가중치오류(
        `${주소} 를 불러올 수 없습니다 (file:// 에서는 fetch 가 막힙니다)`,
        'web_version 폴더에서 로컬 서버를 띄운 뒤 그 주소로 열어 주세요:\n' +
        '    py -m http.server 8000\n' +
        '    http://localhost:8000/');
    }
    throw new 가중치오류(`${주소} 를 불러올 수 없습니다: ${원인.message}`, 내보내기_안내);
  }
  if (!응답.ok) {
    throw new 가중치오류(`${주소} 를 찾을 수 없습니다 (HTTP ${응답.status})`, 내보내기_안내);
  }
  return 응답;
}

/**
 * 가중치를 읽어 { 텐서이름: Float32Array } 사전을 돌려줍니다.
 * 기준경로는 weights.json 이 들어 있는 폴더입니다. 반드시 상대 경로를 씁니다.
 */
export async function 가중치_불러오기(기준경로 = 'model/') {
  const 설명 = await (await 받아오기(`${기준경로}weights.json`)).json();

  const 이진이름 = 설명.이진파일 || 'weights.bin';
  const 버퍼 = await (await 받아오기(`${기준경로}${이진이름}`)).arrayBuffer();

  const 기대바이트 = 설명.전체개수 * 4;
  if (버퍼.byteLength !== 기대바이트) {
    throw new 가중치오류(
      `${이진이름} 의 크기가 맞지 않습니다. ` +
      `기대 ${기대바이트.toLocaleString()}바이트, 실제 ${버퍼.byteLength.toLocaleString()}바이트`,
      내보내기_안내);
  }

  const 전체 = new Float32Array(버퍼);
  const 텐서 = {};

  for (const 항목 of 설명.텐서목록) {
    const 기대 = 기대하는_모양[항목.이름];
    if (!기대) {
      throw new 가중치오류(
        `모르는 텐서가 들어 있습니다: ${항목.이름}`,
        'desktop_version/model.py 와 web_version/js/모델.js 의 구조가 갈렸습니다.\n' +
        '두 파일과 js/가중치.js 의 기대하는_모양 을 함께 맞춰 주세요.');
    }
    if (항목.모양.length !== 기대.length
        || 항목.모양.some((길이, 자리) => 길이 !== 기대[자리])) {
      throw new 가중치오류(
        `${항목.이름} 의 모양이 다릅니다. ` +
        `기대 [${기대}], 실제 [${항목.모양}]`,
        'desktop_version/model.py 와 web_version/js/모델.js 의 구조가 갈렸습니다.');
    }
    텐서[항목.이름] = 전체.subarray(항목.시작, 항목.시작 + 항목.개수);
  }

  const 빠진것 = Object.keys(기대하는_모양).filter((이름) => !(이름 in 텐서));
  if (빠진것.length > 0) {
    throw new 가중치오류(
      `가중치에 다음 텐서가 없습니다: ${빠진것.join(', ')}`, 내보내기_안내);
  }

  return 텐서;
}
