/**
 * 결과 화면이 확률을 제대로 읽어 표시하는지 확인합니다.
 * 화면.js 는 넘겨받은 요소 안에만 그리므로 분리된 div 로 검사할 수 있습니다.
 */
import { 검사_모음, 같음_확인 } from './검사틀.js';
import { 화면_만들기 } from '../js/화면.js';

function 확률만들기(가장큰자리, 가장큰값) {
  const 확률 = new Float32Array(10);
  const 나머지 = (1 - 가장큰값) / 9;
  확률.fill(나머지);
  확률[가장큰자리] = 가장큰값;
  return 확률;
}

export function 만들기() {
  const 모음 = 검사_모음('화면');

  모음.검사('가장 확률이 높은 숫자와 확신도를 보여 준다', () => {
    const 뿌리 = document.createElement('div');
    const 화면 = 화면_만들기(뿌리);
    화면.결과_표시(확률만들기(7, 0.91), new Uint8ClampedArray(784));

    같음_확인(뿌리.querySelector('.예측숫자').textContent, '7', '예측 숫자');
    같음_확인(뿌리.querySelector('.확신도').textContent.includes('91.0'), true,
      `확신도 문구: ${뿌리.querySelector('.확신도').textContent}`);
  });

  모음.검사('0~9 막대 10개를 모두 그리고 백분율을 적는다', () => {
    const 뿌리 = document.createElement('div');
    const 화면 = 화면_만들기(뿌리);
    화면.결과_표시(확률만들기(3, 0.5), new Uint8ClampedArray(784));

    const 막대들 = 뿌리.querySelectorAll('.막대칸');
    같음_확인(막대들.length, 10, '막대 개수');
    const 값들 = 뿌리.querySelectorAll('.막대값');
    같음_확인(값들.length, 10, '값 표시 개수');
    같음_확인(값들[3].textContent.includes('50.0'), true, `3번 값: ${값들[3].textContent}`);
  });

  모음.검사('예측한 숫자의 줄만 강조된다', () => {
    const 뿌리 = document.createElement('div');
    const 화면 = 화면_만들기(뿌리);
    화면.결과_표시(확률만들기(5, 0.8), new Uint8ClampedArray(784));

    const 줄들 = 뿌리.querySelectorAll('.막대줄');
    같음_확인(줄들[5].classList.contains('뽑힘'), true, '5번 줄 강조');
    같음_확인(줄들[4].classList.contains('뽑힘'), false, '4번 줄은 강조 안 됨');
  });

  모음.검사('초기화하면 물음표와 0.0% 로 돌아간다', () => {
    const 뿌리 = document.createElement('div');
    const 화면 = 화면_만들기(뿌리);
    화면.결과_표시(확률만들기(2, 0.99), new Uint8ClampedArray(784));
    화면.초기화();

    같음_확인(뿌리.querySelector('.예측숫자').textContent, '?', '예측 숫자');
    const 값들 = 뿌리.querySelectorAll('.막대값');
    같음_확인(값들[2].textContent.includes('0.0'), true, `2번 값: ${값들[2].textContent}`);
    같음_확인(뿌리.querySelectorAll('.뽑힘').length, 0, '강조된 줄 없음');
  });

  모음.검사('안내와 오류 문구가 화면에 나타난다', () => {
    const 뿌리 = document.createElement('div');
    const 화면 = 화면_만들기(뿌리);

    화면.안내('아직 아무것도 그리지 않았습니다');
    같음_확인(뿌리.querySelector('.확신도').textContent, '아직 아무것도 그리지 않았습니다', '안내');

    화면.오류('가중치를 불러오지 못했습니다', 'py tools/가중치_내보내기.py');
    const 오류칸 = 뿌리.querySelector('.오류');
    같음_확인(오류칸.hidden, false, '오류칸이 보임');
    같음_확인(오류칸.textContent.includes('py tools/가중치_내보내기.py'), true, '안내문 포함');
  });

  모음.검사('미리보기 캔버스는 28×28 이다', () => {
    const 뿌리 = document.createElement('div');
    화면_만들기(뿌리);
    const 미리보기 = 뿌리.querySelector('.미리보기');
    같음_확인(미리보기.width, 28, '가로');
    같음_확인(미리보기.height, 28, '세로');
  });

  return 모음;
}
