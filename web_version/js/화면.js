/**
 * 인식 결과를 보여 주는 화면입니다.
 * 넘겨받은 요소 안에만 그리므로, 검사에서 분리된 div 로 그대로 확인할 수 있습니다.
 *
 * 데스크톱 draw_predict.py 의 오른쪽 결과 영역과 같은 구성입니다.
 * 여기에 '모델이 실제로 본 28×28' 미리보기를 하나 더 둡니다 — 왜 틀렸는지 바로 보입니다.
 */

const 숫자개수 = 10;
const 미리보기크기 = 28;

export function 화면_만들기(뿌리) {
  뿌리.innerHTML = '';
  뿌리.classList.add('결과판');

  const 제목 = 만들기('h2', '결과제목', '인식 결과');
  const 예측숫자 = 만들기('div', '예측숫자', '?');
  const 확신도 = 만들기('p', '확신도', '숫자를 써 보세요');

  // 변수 이름을 '오류칸'으로 둡니다. 아래 반환 객체에 '오류' 메서드가 있어 헷갈리기 쉽습니다.
  const 오류칸 = 만들기('pre', '오류', '');
  오류칸.hidden = true;

  const 막대제목 = 만들기('h3', '막대제목', '숫자별 확률');
  const 막대판 = 만들기('div', '막대판', '');

  const 막대들 = [];
  for (let 숫자 = 0; 숫자 < 숫자개수; 숫자++) {
    const 줄 = 만들기('div', '막대줄', '');
    줄.appendChild(만들기('span', '막대이름', String(숫자)));

    const 홈 = 만들기('span', '막대홈', '');
    const 칸 = 만들기('span', '막대칸', '');
    칸.style.width = '0%';
    홈.appendChild(칸);
    줄.appendChild(홈);

    const 값 = 만들기('span', '막대값', '0.0%');
    줄.appendChild(값);

    막대판.appendChild(줄);
    막대들.push({ 줄, 칸, 값 });
  }

  const 미리보기제목 = 만들기('h3', '미리보기제목', '모델이 본 그림 (28×28)');
  const 미리보기 = document.createElement('canvas');
  미리보기.className = '미리보기';
  미리보기.width = 미리보기크기;
  미리보기.height = 미리보기크기;
  const 미리보기맥락 = 미리보기.getContext('2d');

  뿌리.append(제목, 예측숫자, 확신도, 오류칸, 막대제목, 막대판, 미리보기제목, 미리보기);

  function 만들기(태그, 클래스, 글) {
    const 요소 = document.createElement(태그);
    요소.className = 클래스;
    요소.textContent = 글;
    return 요소;
  }

  function 미리보기_그리기(값들) {
    const 그림 = 미리보기맥락.createImageData(미리보기크기, 미리보기크기);
    for (let i = 0; i < 미리보기크기 * 미리보기크기; i++) {
      // 모델이 보는 것은 '검은 배경 · 흰 글씨' 입니다. 그대로 보여 줍니다.
      const 밝기 = 값들[i];
      그림.data[i * 4] = 밝기;
      그림.data[i * 4 + 1] = 밝기;
      그림.data[i * 4 + 2] = 밝기;
      그림.data[i * 4 + 3] = 255;
    }
    미리보기맥락.putImageData(그림, 0, 0);
  }

  return {
    /** 확률 10개와 28×28 미리보기를 화면에 반영합니다. */
    결과_표시(확률, 미리보기값) {
      오류칸.hidden = true;
      let 뽑힌숫자 = 0;
      for (let 숫자 = 1; 숫자 < 숫자개수; 숫자++) {
        if (확률[숫자] > 확률[뽑힌숫자]) 뽑힌숫자 = 숫자;
      }

      예측숫자.textContent = String(뽑힌숫자);
      확신도.textContent = `확신도 ${(확률[뽑힌숫자] * 100).toFixed(1)}%`;

      for (let 숫자 = 0; 숫자 < 숫자개수; 숫자++) {
        const { 줄, 칸, 값 } = 막대들[숫자];
        칸.style.width = `${확률[숫자] * 100}%`;
        값.textContent = `${(확률[숫자] * 100).toFixed(1)}%`;
        줄.classList.toggle('뽑힘', 숫자 === 뽑힌숫자);
      }

      if (미리보기값) 미리보기_그리기(미리보기값);
    },

    /** 물음표와 0% 로 되돌립니다. */
    초기화() {
      오류칸.hidden = true;
      예측숫자.textContent = '?';
      확신도.textContent = '숫자를 써 보세요';
      for (const { 줄, 칸, 값 } of 막대들) {
        칸.style.width = '0%';
        값.textContent = '0.0%';
        줄.classList.remove('뽑힘');
      }
      미리보기_그리기(new Uint8ClampedArray(미리보기크기 * 미리보기크기));
    },

    /** 확신도 자리에 한 줄 안내를 띄웁니다. */
    안내(문구) {
      확신도.textContent = 문구;
    },

    /** 복구 방법까지 담은 오류를 띄웁니다. */
    오류(제목글, 안내문) {
      예측숫자.textContent = '!';
      확신도.textContent = 제목글;
      오류칸.textContent = 안내문;
      오류칸.hidden = false;
    },

    /** 가중치를 받는 동안처럼 기다려야 할 때 표시를 켭니다. */
    바쁨(켬) {
      뿌리.classList.toggle('바쁨', 켬);
    },
  };
}
