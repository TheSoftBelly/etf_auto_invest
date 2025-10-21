import csv
import os
from datetime import datetime
from pathlib import Path

class CSVManager:
    """CSV 파일 관리 클래스"""
    
    def __init__(self, data_dir='data', reports_dir='reports'):
        self.data_dir = Path(data_dir)
        self.reports_dir = Path(reports_dir)
        
        # 디렉토리 생성
        self.data_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
        # 파일 경로
        self.portfolio_file = self.data_dir / 'portfolio.csv'
        self.trade_history_file = self.data_dir / 'trade_history.csv'
        self.price_history_file = self.data_dir / 'price_history.csv'
        self.monthly_stats_file = self.data_dir / 'monthly_stats.csv'
        
        # CSV 파일 초기화
        self._init_csv_files()
    
    def _init_csv_files(self):
        """CSV 파일 초기화 (헤더 생성)"""
        
        # 포트폴리오 CSV
        if not self.portfolio_file.exists():
            with open(self.portfolio_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'ETF코드', 'ETF명', '보유수량', '평균단가', 
                    '현재가', '평가금액', '투자금액', '평가손익', 
                    '수익률(%)', '최종수정일시'
                ])
        
        # 매매기록 CSV
        if not self.trade_history_file.exists():
            with open(self.trade_history_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    '거래일시', '구분', 'ETF코드', 'ETF명', 
                    '매매단가', '수량', '총금액', '수수료', 
                    '메모'
                ])
        
        # 가격기록 CSV
        if not self.price_history_file.exists():
            with open(self.price_history_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    '날짜', 'ETF코드', 'ETF명', '현재가', 
                    '52주최고가', '52주최저가', '전일대비', 
                    '하락률(%)', '상태'
                ])
        
        # 월간통계 CSV
        if not self.monthly_stats_file.exists():
            with open(self.monthly_stats_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    '년월', '정기매수액', '기회매수액', '월합계', 
                    '누적투자금', '월말평가액', '월간수익률(%)', 
                    '누적수익률(%)', '메모'
                ])
    
    def add_trade(self, trade_data):
        """매매 기록 추가
        
        Args:
            trade_data (dict): {
                'type': '정기' or '기회',
                'code': 'ETF코드',
                'name': 'ETF명',
                'price': 매매단가,
                'quantity': 수량,
                'total': 총금액,
                'fee': 수수료,
                'memo': '메모'
            }
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.trade_history_file, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                now,
                trade_data['type'],
                trade_data['code'],
                trade_data['name'],
                trade_data['price'],
                trade_data['quantity'],
                trade_data['total'],
                trade_data.get('fee', 0),
                trade_data.get('memo', '')
            ])
        
        print(f"✅ 매매기록 저장: {trade_data['name']} {trade_data['quantity']}주")
    
    def update_portfolio(self, portfolio_data):
        """포트폴리오 업데이트
        
        Args:
            portfolio_data (list): [{
                'code': 'ETF코드',
                'name': 'ETF명',
                'quantity': 보유수량,
                'avg_price': 평균단가,
                'current_price': 현재가,
                'eval_amt': 평가금액,
                'invest_amt': 투자금액,
                'profit_loss': 평가손익,
                'profit_rate': 수익률
            }, ...]
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.portfolio_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            # 헤더
            writer.writerow([
                'ETF코드', 'ETF명', '보유수량', '평균단가', 
                '현재가', '평가금액', '투자금액', '평가손익', 
                '수익률(%)', '최종수정일시'
            ])
            
            # 데이터
            for item in portfolio_data:
                writer.writerow([
                    item['code'],
                    item['name'],
                    item['quantity'],
                    item['avg_price'],
                    item['current_price'],
                    item['eval_amt'],
                    item['invest_amt'],
                    item['profit_loss'],
                    f"{item['profit_rate']:.2f}",
                    now
                ])
        
        print(f"✅ 포트폴리오 업데이트 완료 ({len(portfolio_data)}개 종목)")
    
    def add_price_record(self, price_data):
        """가격 기록 추가
        
        Args:
            price_data (dict): {
                'code': 'ETF코드',
                'name': 'ETF명',
                'current_price': 현재가,
                'high_52w': 52주최고가,
                'low_52w': 52주최저가,
                'prev_close': 전일종가,
                'drop_rate': 하락률,
                'status': '상태'
            }
        """
        today = datetime.now().strftime('%Y-%m-%d')
        prev_close = price_data.get('prev_close', 0)
        current = price_data['current_price']
        change = current - prev_close if prev_close else 0
        
        with open(self.price_history_file, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                today,
                price_data['code'],
                price_data['name'],
                price_data['current_price'],
                price_data['high_52w'],
                price_data['low_52w'],
                change,
                f"{price_data['drop_rate']:.2f}",
                price_data['status']
            ])
    
    def add_monthly_stat(self, stat_data):
        """월간 통계 추가
        
        Args:
            stat_data (dict): {
                'year_month': '2025-11',
                'regular_buy': 정기매수액,
                'dip_buy': 기회매수액,
                'monthly_total': 월합계,
                'cumulative_invest': 누적투자금,
                'month_end_eval': 월말평가액,
                'monthly_return': 월간수익률,
                'cumulative_return': 누적수익률,
                'memo': '메모'
            }
        """
        with open(self.monthly_stats_file, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                stat_data['year_month'],
                stat_data['regular_buy'],
                stat_data['dip_buy'],
                stat_data['monthly_total'],
                stat_data['cumulative_invest'],
                stat_data['month_end_eval'],
                f"{stat_data['monthly_return']:.2f}",
                f"{stat_data['cumulative_return']:.2f}",
                stat_data.get('memo', '')
            ])
        
        print(f"✅ {stat_data['year_month']} 월간통계 저장 완료")
    
    def get_portfolio(self):
        """포트폴리오 조회"""
        if not self.portfolio_file.exists():
            return []
        
        with open(self.portfolio_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            return list(reader)
    
    def get_trade_history(self, start_date=None, end_date=None):
        """매매 기록 조회"""
        if not self.trade_history_file.exists():
            return []
        
        with open(self.trade_history_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            trades = list(reader)
        
        # 날짜 필터링
        if start_date or end_date:
            filtered = []
            for trade in trades:
                trade_date = datetime.strptime(trade['거래일시'], '%Y-%m-%d %H:%M:%S')
                
                if start_date and trade_date < start_date:
                    continue
                if end_date and trade_date > end_date:
                    continue
                
                filtered.append(trade)
            return filtered
        
        return trades
    
    def get_monthly_stats(self, year_month=None):
        """월간 통계 조회"""
        if not self.monthly_stats_file.exists():
            return []
        
        with open(self.monthly_stats_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            stats = list(reader)
        
        if year_month:
            return [s for s in stats if s['년월'] == year_month]
        
        return stats
    
    def calculate_portfolio_stats(self):
        """포트폴리오 통계 계산"""
        portfolio = self.get_portfolio()
        
        if not portfolio:
            return {
                'total_invest': 0,
                'total_eval': 0,
                'total_profit_loss': 0,
                'total_profit_rate': 0,
                'stock_count': 0
            }
        
        total_invest = sum(float(p['투자금액']) for p in portfolio)
        total_eval = sum(float(p['평가금액']) for p in portfolio)
        total_profit_loss = total_eval - total_invest
        total_profit_rate = (total_profit_loss / total_invest * 100) if total_invest > 0 else 0
        
        return {
            'total_invest': total_invest,
            'total_eval': total_eval,
            'total_profit_loss': total_profit_loss,
            'total_profit_rate': total_profit_rate,
            'stock_count': len(portfolio)
        }
    
    def export_weekly_report(self):
        """주간 리포트 CSV 생성"""
        today = datetime.now()
        filename = f"weekly_report_{today.strftime('%Y_%m_%d')}.csv"
        filepath = self.reports_dir / filename
        
        portfolio = self.get_portfolio()
        stats = self.calculate_portfolio_stats()
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 요약 정보
            writer.writerow(['📊 주간 투자 리포트'])
            writer.writerow(['생성일시', today.strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            
            writer.writerow(['구분', '금액'])
            writer.writerow(['총 투자금액', f"{stats['total_invest']:,.0f}원"])
            writer.writerow(['총 평가금액', f"{stats['total_eval']:,.0f}원"])
            writer.writerow(['평가손익', f"{stats['total_profit_loss']:,.0f}원"])
            writer.writerow(['수익률', f"{stats['total_profit_rate']:.2f}%"])
            writer.writerow([])
            
            # 포트폴리오 상세
            writer.writerow(['📈 보유 종목 현황'])
            writer.writerow([
                'ETF명', '보유수량', '평균단가', '현재가', 
                '평가금액', '평가손익', '수익률(%)'
            ])
            
            for p in portfolio:
                writer.writerow([
                    p['ETF명'],
                    p['보유수량'],
                    f"{float(p['평균단가']):,.0f}원",
                    f"{float(p['현재가']):,.0f}원",
                    f"{float(p['평가금액']):,.0f}원",
                    f"{float(p['평가손익']):,.0f}원",
                    f"{p['수익률(%)']}%"
                ])
        
        print(f"✅ 주간 리포트 생성: {filepath}")
        return str(filepath)
    
    def export_monthly_report(self, year_month=None):
        """월간 리포트 CSV 생성"""
        if not year_month:
            year_month = datetime.now().strftime('%Y-%m')
        
        filename = f"monthly_report_{year_month.replace('-', '_')}.csv"
        filepath = self.reports_dir / filename
        
        # 해당 월의 거래 내역
        start_date = datetime.strptime(f"{year_month}-01", '%Y-%m-%d')
        year, month = map(int, year_month.split('-'))
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        trades = self.get_trade_history(start_date, end_date)
        stats = self.calculate_portfolio_stats()
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 제목
            writer.writerow([f'📊 {year_month} 월간 투자 리포트'])
            writer.writerow(['생성일시', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            
            # 월간 요약
            regular_total = sum(float(t['총금액']) for t in trades if t['구분'] == '정기')
            dip_total = sum(float(t['총금액']) for t in trades if t['구분'] == '기회')
            
            writer.writerow(['📅 월간 투자 내역'])
            writer.writerow(['구분', '금액'])
            writer.writerow(['정기 매수', f"{regular_total:,.0f}원"])
            writer.writerow(['기회 매수', f"{dip_total:,.0f}원"])
            writer.writerow(['월간 합계', f"{regular_total + dip_total:,.0f}원"])
            writer.writerow([])
            
            # 포트폴리오 현황
            writer.writerow(['💰 포트폴리오 현황'])
            writer.writerow(['구분', '금액'])
            writer.writerow(['총 투자금액', f"{stats['total_invest']:,.0f}원"])
            writer.writerow(['총 평가금액', f"{stats['total_eval']:,.0f}원"])
            writer.writerow(['평가손익', f"{stats['total_profit_loss']:,.0f}원"])
            writer.writerow(['수익률', f"{stats['total_profit_rate']:.2f}%"])
            writer.writerow([])
            
            # 거래 내역
            writer.writerow(['📝 거래 내역'])
            writer.writerow([
                '거래일시', '구분', 'ETF명', '매매단가', 
                '수량', '총금액', '메모'
            ])
            
            for trade in trades:
                writer.writerow([
                    trade['거래일시'],
                    trade['구분'],
                    trade['ETF명'],
                    f"{float(trade['매매단가']):,.0f}원",
                    trade['수량'],
                    f"{float(trade['총금액']):,.0f}원",
                    trade['메모']
                ])
        
        print(f"✅ 월간 리포트 생성: {filepath}")
        return str(filepath)

# 테스트 코드
if __name__ == "__main__":
    csv_mgr = CSVManager()
    
    # 테스트 데이터
    trade = {
        'type': '정기',
        'code': '133690',
        'name': 'TIGER 미국나스닥100',
        'price': 159215,
        'quantity': 3,
        'total': 477645,
        'fee': 0,
        'memo': '11월 정기매수'
    }
    
    csv_mgr.add_trade(trade)
    print("✅ CSV Manager 테스트 완료")