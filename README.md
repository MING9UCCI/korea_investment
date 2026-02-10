# 🦅 Zero-Cost AI Trading Bot (Antigravity)

> **"Serverless, Zero-Cost, AI-Driven."**
> 
> 국내(KR) 및 미국(US) 주식 시장을 AI(Gemini 2.5)가 분석하여 24시간 자동으로 매매하는 **서버비 0원** 프로젝트입니다.

![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen) ![Python](https://img.shields.io/badge/Python-3.10-blue) ![License](https://img.shields.io/badge/License-MIT-green)

---

## 🏗️ Architecture & Tech Stack

이 프로젝트는 비용 효율성과 확장성을 최우선으로 설계되었습니다.

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Execution** | **GitHub Actions** | 별도의 서버 없이 Cron 스케줄러로 코드를 실행 (Serverless) |
| **Brokerage** | **Korea Investment (KIS)** | 한국투자증권 Open API (국내/해외 통합 매매) |
| **AI Brain** | **Google Gemini 2.5 Flash** | 뉴스 감성 분석, 포트폴리오 리밸런싱, 매매 의사결정 |
| **Notification** | **Discord Webhook** | 실시간 체결 알림 및 일일 시황 브리핑 (채널 이원화) |
| **Scheduling** | **Holidays Library** | 한국/미국 휴장일을 자동 감지하여 불필요한 실행 방지 |

---

## 🔥 Key Features

### 1. 🤖 AI 포트폴리오 매니저
단순한 기술적 지표(RSI, 볼린저밴드)를 넘어, **LLM(Gemini)**이 시장 상황을 종합적으로 판단합니다.
- **Sentiment Analysis**: 최신 뉴스를 분석하여 시장의 공포/탐욕 지수를 파악합니다.
- **Dynamic Switching**: 보유 종목보다 더 유망한 종목이 발견되면 과감하게 교체(Switching) 매매를 수행합니다.
- **Risk Management**: 악재가 발생한 기업은 즉시 매도하여 리스크를 최소화합니다.

### 2. 🌍 Global Trading (KR & US)
- **Hybrid Market**: 낮에는 한국장(KOSPI/KOSDAQ), 밤에는 미국장(NASDAQ/NYSE)을 모두 커버합니다.
- **Automated Exchange**: 통합증거금 서비스를 통해 원화(KRW) 하나로 미국 주식까지 거래합니다.

### 3. 🛡️ Dual Environment (Virtual vs Real)
- **Safety First**: `config.py` 설정 하나로 **모의투자**와 **실전투자**를 즉시 전환할 수 있습니다.
- **Seamless Switch**: 코드를 수정할 필요 없이, GitHub Secrets 교체나 `KIS_MODE` 변경만으로 모드가 바뀝니다.

### 4. 📊 Professional Reporting
- **Trading Alert**: 매매 체결 시, 디스코드 트레이딩 채널에 실시간으로 알림을 보냅니다. (매수/매도 사유 + **체결 차트 이미지** + **뉴스 원문 링크** 포함)
- **Daily Briefing**: 매일 아침 08:50(장 시작 전), AI가 작성한 고품질 시황 브리핑을 발송합니다.
- **Daily Summary**: 매일 오후 15:30(장 마감 후), 내 자산 변동 리포트를 발송합니다.

### 5. 📈 Asset Dashboard
- **Web Dashboard**: 내 자산이 우상향하고 있는지, 그래프로 한눈에 확인하세요.
- **URL**: `https://USER_NAME.github.io/korea_investment/` (GitHub Pages 연동 시)

---

## 🚀 Getting Started

### 1. Prerequisites
- 한국투자증권 계좌 (실전/모의)
- GitHub 계정
- Discord 채널 (알림 수신용)

### 2. Installation
```bash
# 1. Clone this repository
git clone https://github.com/YOUR_USERNAME/korea_investment.git
cd korea_investment

# 2. Install dependencies (Local Test)
pip install -r requirements.txt

# 3. Security Setup
# Create .env file for local testing (Do NOT commit this file)
cp .env.example .env
```

### 3. GitHub Secrets Setup
Go to **Settings > Secrets and variables > Actions** and add:

| Secret Name | Description |
| :--- | :--- |
| `KIS_MODE` | `VIRTUAL` or `REAL` |
| `KIS_APP_KEY_VIRTUAL` | Mock Trading App Key |
| `KIS_APP_SECRET_VIRTUAL` | Mock Trading App Secret |
| `KIS_CANO_VIRTUAL` | Mock Account Number (8 digits) |
| `KIS_APP_KEY_REAL` | Real Trading App Key |
| `KIS_APP_SECRET_REAL` | Real Trading App Secret |
| `KIS_CANO_REAL` | Real Account Number (8 digits) |
| `GEMINI_API_KEY` | Google AI API Key |
| `DISCORD_WEBHOOK_TRADING` | Webhook URL for Alerts |
| `DISCORD_WEBHOOK_BRIEFING` | Webhook URL for Reports |

---

## 📈 Dashboard (Reports)
All trading reports are automatically generated and saved in the `reports/` directory of this repository. You can check the daily logs and performance history directly on GitHub.

---

## ☕ Disclaimer
이 프로젝트는 개인의 학습 및 자동화 연구를 목적으로 개발되었습니다.
**투자의 책임은 전적으로 사용자 본인에게 있습니다.** 
모의투자(Virtual) 환경에서 충분한 테스트 후 실전(Real)에 적용하시기 바랍니다.
