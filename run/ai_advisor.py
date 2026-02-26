import sqlite3
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import google.generativeai as genai
from config.config_manager import config_manager
from core.logger import get_logger, db_logger
import discord_notifier

logger = get_logger("ai_improvement")

class AIAdvisor:
    def __init__(self):
        self.api_key = config_manager.gemini_api_key
        if not self.api_key:
            logger.error("No Gemini API key found for AI Advisor.")
            return
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def fetch_recent_trades(self, days=7):
        """최근 N일간의 거래 내역을 DB에서 가져옴"""
        try:
            conn = sqlite3.connect("trade_logs.db")
            target_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            query = f"""
                SELECT timestamp, market, code, name, signal, reason, action, price, qty
                FROM trade_history
                WHERE timestamp >= '{target_date}'
                ORDER BY timestamp ASC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Failed to fetch trades: {e}")
            return pd.DataFrame()

    def generate_improvement_report(self):
        """거래 내역을 AI에게 제공하고 개선 리포트 생성"""
        if not self.api_key: return "AI API Key missing."

        df = self.fetch_recent_trades(7)
        if df.empty:
            return "최근 7일간 거래 내역이 없어 분석할 수 없습니다."
            
        # 프롬프트에 넣기 위해 요약된 텍스트로 변환
        trades_text = df.to_csv(index=False)
        
        prompt = f"""
당신은 퀀트 트레이딩 AI입니다. 다음은 지난 7일간의 모의/실전 거래 내역입니다.

[거래내역]
{trades_text}

[요청사항]
1. 위 거래의 승률과 패인이 무엇인지 짧게 요약해주세요. (시장 추세와 매수 시점의 괴리 등)
2. 현재 TrendFollowing 전략의 손절(-3%), 익절(+7%) 파라미터가 적절했는지 데이터 기반으로 평가해주세요.
3. 파라미터를 어떻게 튜닝하는 것이 좋을지 구체적인 제안(예: "손절선을 -4%로 늘리고 익절을 +5%로 корот게")을 해주세요.
4. 어떤 조건식(변동성 필터 등)을 추가하면 승률이 올라갈지 제안해주세요.
답변은 읽기 쉽게 Markdown 형식으로 1500자 이내로 작성하세요.
"""
        logger.info("Requesting Gemini AI for Performance Analysis...")
        try:
            response = self.model.generate_content(prompt)
            report = response.text
            
            # 파일로 저장
            report_path = f"reports/ai_insight_{datetime.now().strftime('%Y%m%d')}.md"
            os.makedirs("reports", exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)
                
            logger.info(f"AI Improvement Report generated at {report_path}")
            
            # 디스코드로 전송
            discord_notifier.send_message(f"🧠 **[주간 AI 자동매매 성과 피드백]**\n\n{report}", type="briefing")
            
            return report
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return f"Error during AI analysis: {e}"

if __name__ == '__main__':
    advisor = AIAdvisor()
    advisor.generate_improvement_report()
