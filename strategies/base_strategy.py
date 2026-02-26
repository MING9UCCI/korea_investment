from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, name, params):
        self.name = name
        self.params = params

    @abstractmethod
    def analyze(self, df: pd.DataFrame, current_holdings: list) -> tuple[str, str, float]:
        """
        데이터프레임을 분석하여 매매 시그널을 반환합니다.
        
        Args:
            df (pd.DataFrame): 일봉/분봉 차트 데이터 (시간순 정렬)
            current_holdings (list): 현재 계좌 보유 종목 리스트 (해당 종목 여부 파악용)
            
        Returns:
            tuple:
                signal (str): "BUY", "SELL", "HOLD"
                reason (str): 시그널 발생 사유 로깅용 텍스트
                target_peso (float): 매수 시 목표 자산 대비 비중 (예: 0.05 -> 전체 자산의 5%)
        """
        pass
