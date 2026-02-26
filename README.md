# 🦅 Zero-Cost AI Trading Bot (Antigravity) - V2 Architecture

> **"안정성, 모듈화, 리스크 관리 우선 기반의 자동매매 시스템"**
> 
> 한국투자증권 Open API를 활용하여 국내 주식 스윙·단기 추세 추종 전략을 수행하는 로컬/서버 데몬 형태의 자동매매 시스템입니다.

---

## 🏗️ Architecture & Component

단일 스크립트 기반 동작을 탈피하여 철저한 리스크 관리와 지속적 운영이 가능한 모듈 구조로 개편되었습니다.

```text
korea_investment/
├── config/               # 환경 설정 (API 키, 전략 파라미터 분리)
│   ├── api_config.yaml
│   └── trading_config.yaml
├── core/                 # 통신 및 기본 골격 로직
│   ├── kis_client.py     # 인증 자동화 및 지수 백오프 기반 HTTP 요청
│   ├── data_feed.py      # 실시간 호가/일봉 데이터 수집
│   ├── order_executor.py # 주문 전송 모듈
│   └── logger.py         # SQLite DB 기반 트레이드/에러 로거
├── risk/                 # 리스크 관리 (최우선 거름망)
│   └── risk_manager.py   # 계좌 일일 손실 한도(-3%) 및 단일 종목 최대 비중(10%) 통제
├── strategies/           # 분리형 매매 전략군
│   ├── base_strategy.py  
│   ├── trend_following.py# 단기 이평/거래량 돌파 기반 추세 추종 (메인)
│   └── mean_reversion.py # 과매도 낙폭 과대 반등 (서브)
├── run/                  # 실행 데몬 (진입점)
│   ├── run_paper.py      # 모의투자 전용 루프 데몬
│   ├── run_live.py       # 실전용 루프 데몬 (초기 자본 축소, 추가 AI 억제 로직 적용)
│   └── ai_advisor.py     # 생성형 AI 기반 주간 성과 피드백 생성
└── backtest/             # 과거 데이터 성과 검증
    └── backtest_engine.py# MDD, 수수료, 슬리피지 기반 시뮬레이터
```

---

## 🔥 Key Features (V2)

### 1. 🛡️ 리스크 퍼스트 매니지먼트 (Risk Manager)
- **일간 최대 손실 제한(Daily Loss Limit)**: 총 자산 대비 `-3%` 등 설정된 한도 이상 손실 발생 시 **당일 신규 진입 즉각 중단**. (추가 손실 방어)
- **종목 분산 한도(Max Weight)**: 철저한 분산을 위해 단일 종목에는 자산의 최대 `10%` 까지만 투입하도록 수량 자동 조절 다운사이징.

### 2. 🧠 전략-인프라 완전 분리
- **객체 지향 전략 구성**: `BaseStrategy` 상속을 통해 누구나 쉽게 나만의 차트 전략 추가 가능. 
- 복수 개의 전략(현재는 추세 추종, 단기 되돌림)이 독립적으로 신호를 만들면 메인 루프에서 최적의 액션을 채택합니다.

### 3. 🤖 AI 인사이트 어드바이저 (AI Improvement Loop)
- **SQLite Trade Log**: 모든 매매 시그널, 체결가, 수량을 데이터베이스(`trade_logs.db`)에 영구 보존.
- **Gemini 피드백 루프**: 주 1회 `run/ai_advisor.py`를 실행하여 최근 7일간의 매매 내역을 AI가 평가하고 개선 제안(RSI Period, 손절 % 최적화 가이드) 제공.

### 4. 📈 내장형 백테스트 엔진 (Backtest Simulator)
- API 데이터 또는 증권사 데이터를 이용해 실제 과거 시장 상황에 코드를 던져 수익률(Return)과 최대 낙폭(MDD)을 파악하는 `backtest_engine.py` 탑재.
- 실전(Live) 전환 전 파라미터 적합성을 테스트해 볼 수 있습니다.

---

## 🚀 Getting Started

### 1. 설정 세팅 (Configuration)

기본 스캐폴딩 내 `config/` 디렉토리에 위치한 파일을 수정합니다.

- **`config/api_config.yaml`** : 
  - 한국투자증권 MOCK(모의) / REAL(실전) 앱 키와 계좌번호 입력.
  - Gemini API Key 설정
  - (옵션) Discord Webhook 입력
- **`config/trading_config.yaml`** :
  - `system.mode`: `VIRTUAL` or `REAL`
  - 전략별 손절/익절/Trailing Stop 파라미터 및 최대 비중 세팅.

### 2. 가상 환경 구축 및 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 모의투자 구동 (Paper Trading 데몬)

실전 계좌로 전환하기 전에 최소 며칠 간 이 데몬으로 안정성을 파악하세요.

```bash
python run/run_paper.py
```

### 4. 성과 분석 및 실전 투입

1. `python backtest/backtest_engine.py` 로 파라미터 백테스트 
2. 주 1회 `python run/ai_advisor.py` 로 AI 평가 받기
3. 검증 완료 후 **`api_config.yaml`에서 Mode를 `REAL`로 바꾸고** `python run/run_live.py` 실행! (※ 실전투자는 리스크 한도가 강제 축소 적용되어 시작합니다)

---

## ☕ Disclaimer
이 프로젝트는 철저히 파이썬 오픈소스 학습 및 퀀트 튜토리얼용으로 제공됩니다. 
한국투자증권 운영 가이드라인을 준수하며, **이 프로그램을 이용한 매매 손익의 책임은 전적으로 사용자 본인에게 있습니다.** 
실전(Live) 환경 적용 전 반드시 모의투자 플로우에서 충분한 안정성 확보를 선행하시기 바랍니다.
