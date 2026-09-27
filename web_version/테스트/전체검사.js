/**
 * 검사 모음을 전부 모아 실행합니다.
 * DOM 을 건드리지 않으므로 브라우저(자가진단.html)와 Node 양쪽에서 호출할 수 있습니다.
 *
 * 인자:
 *   고정표본 - 테스트/고정표본.json 을 파싱한 객체
 *   텐서     - 가중치 텐서 사전. 아직 없으면 null 을 넘깁니다(모델 검사는 건너뜁니다).
 */
import * as 검사틀검사 from './검사틀_검사.js';
import * as 리샘플검사 from './리샘플_검사.js';

export async function 전체검사_실행(고정표본, 텐서 = null) {
  const 모음들 = [
    검사틀검사.만들기(),
    리샘플검사.만들기(고정표본),
  ];
  void 텐서;

  const 결과들 = [];
  for (const 모음 of 모음들) {
    결과들.push(await 모음.실행());
  }
  return 결과들;
}
