/**
 * 웹 버전의 진입점입니다. 각 조각을 이어 붙이고 오류를 사용자에게 설명합니다.
 *
 * 흐름: 그림판 → 전처리 → 순전파 → 화면
 */
import { 가중치_불러오기, 가중치오류 } from './가중치.js';
import { 그림판_만들기, 칠판크기 } from './그림판.js';
import { MNIST_형식으로_변환 } from './전처리.js';
import { 예측 } from './모델.js';
import { 화면_만들기 } from './화면.js';

const 화면캔버스 = document.getElementById('화면캔버스');
const 모델캔버스 = document.getElementById('모델캔버스');
const 인식단추 = document.getElementById('인식단추');
const 지우기단추 = document.getElementById('지우기단추');
const 화면 = 화면_만들기(document.getElementById('결과'));

let 텐서 = null;

const 그림판 = 그림판_만들기(화면캔버스, 모델캔버스, {
  그리기끝나면: 인식하기,   // 데스크톱과 같이 손을 떼면 바로 인식합니다.
});

function 단추_잠금(잠글까) {
  인식단추.disabled = 잠글까;
  지우기단추.disabled = 잠글까;
}

function 인식하기() {
  if (텐서 === null) return;

  const 변환 = MNIST_형식으로_변환(그림판.회색조_가져오기(), 칠판크기, 칠판크기);
  if (변환 === null) {
    화면.안내('아직 아무것도 그리지 않았습니다');
    return;
  }

  const 시작 = performance.now();
  const { 숫자, 확률 } = 예측(변환.정규화배열, 텐서);
  const 걸린시간 = Math.round(performance.now() - 시작);

  화면.결과_표시(확률, 변환.미리보기);
  console.log(`인식 결과: ${숫자} (확신도 ${(확률[숫자] * 100).toFixed(1)}%, ${걸린시간}ms)`);
}

function 지우기() {
  그림판.지우기();
  화면.초기화();
}

인식단추.addEventListener('click', 인식하기);
지우기단추.addEventListener('click', 지우기);

document.addEventListener('keydown', (사건) => {
  if (사건.key === 'Enter') {
    사건.preventDefault();
    인식하기();
  } else if (사건.key === 'c' || 사건.key === 'C') {
    지우기();
  }
});

async function 시작하기() {
  화면.초기화();
  화면.바쁨(true);
  단추_잠금(true);
  화면.안내('모델을 불러오는 중… (약 4.6MB)');

  try {
    텐서 = await 가중치_불러오기('model/');
  } catch (오류) {
    화면.바쁨(false);
    if (오류 instanceof 가중치오류) {
      화면.오류(오류.message, 오류.안내);
    } else {
      화면.오류('모델을 불러오지 못했습니다', String(오류));
    }
    console.error(오류);
    return;
  }

  화면.바쁨(false);
  단추_잠금(false);
  화면.안내('숫자를 써 보세요');
}

시작하기();
