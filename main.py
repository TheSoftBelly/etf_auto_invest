#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ETF 자동투자 시스템
- ISA 계좌 지원
- 월별 분할 매수 전략
- -5% 하락 시 기회 매수
- 디스코드 알림
- CSV 자동 기록
"""

import time
import schedule
from datetime import datetime, timedelta
import sys
import traceback

from modules.strategy import TradingStrategy
from modules.discord_bot import DiscordBot
from modules.csv_manager import CSVManager
import yaml

class ETFAutoInvestor:
    """ETF 자동투자 메인 시스템"""
    
    def __init__(self, config_path='config.yaml'):
        print("\n" + "="*70)
        print("🚀 ETF 자동투자 시스템 시작")
        print("="*70 + "\n")
        
        # 설정 로드
        with open(config_path, encoding='UTF-8') as f:
            self.cfg = yaml.load(f, Loader=yaml.FullLoader)
        
        # 모듈 초기화
        try:
            self.strategy = TradingStrategy(config_path)
            self.discord = self.strategy.discord
            self.csv = CSVManager()
            
            # 시스템 시작 알림
            self.discord.send_system_start()
            
            # 스케줄 설정
            self._setup_schedule()
            
            print("\n✅ 시스템 초기화 완료\n")
            
        except Exception as e:
            print(f"\n❌ 초기화 실패: {e}")
            traceback.print_exc()
            sys.exit(1)
    
    def _setup_schedule(self):
        """스케줄 설정"""
        
        notifications = self.cfg.get('NOTIFICATIONS', {})
        
        # 1. 아침 리포트 (오전 9시)
        if notifications.get('morning_report', True):
            schedule.every().day.at("09:00").do(self.morning_report)
            print("📅 스케줄 등록: 아침 리포트 (매일 09:00)")
        
        # 2. 정기 매수일 체크 (오전 9시 5분)
        schedule.every().day.at("09:05").do(self.check_regular_buy)
        print("📅 스케줄 등록: 정기 매수 체크 (매일 09:05)")
        
        # 3. 하락 매수 기회 체크 (30분마다, 장 중)
        if notifications.get('price_alert', True):
            schedule.every(30).minutes.do(self.check_dip_buy)
            print("📅 스케줄 등록: 하락 체크 (30분마다)")
        
        # 4. 주간 리포트 (월요일 오전 9시)
        if notifications.get('weekly_report', True):
            schedule.every().monday.at("09:00").do(self.weekly_report)
            print("📅 스케줄 등록: 주간 리포트 (월요일 09:00)")
        
        # 5. 월간 리포트 (매월 1일 오전 9시)
        if notifications.get('monthly_report', True):
            schedule.every().day.at("09:00").do(self.check_monthly_report)
            print("📅 스케줄 등록: 월간 리포트 체크 (매일 09:00)")
        
        # 6. 포트폴리오 업데이트 (장 마감 후)
        schedule.every().day.at("15:35").do(self.update_portfolio)
        print("📅 스케줄 등록: 포트폴리오 업데이트 (매일 15:35)")
        
        print()
    
    def morning_report(self):
        """아침 시장 리포트"""
        
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🌅 아침 리포트 전송 중...")
            
            # 현재가 조회
            etf_prices = []
            for etf in self.strategy.allocator.active_etfs:
                code = etf['code']
                price_data = self.strategy.api.get_domestic_etf_price(code)
                
                if price_data:
                    high_52w = self.strategy.high_52w_cache.get(code, price_data['high_52w'])
                    drop_rate = ((price_data['current_price'] - high_52w) / high_52w) * 100
                    
                    etf_prices.append({
                        'name': etf['name'],
                        'current_price': price_data['current_price'],
                        'drop_rate': drop_rate,
                        'change': price_data.get('change', 0),
                        'change_rate': price_data.get('change_rate', 0)
                    })
                    
                    # CSV 가격 기록
                    status = "정상" if drop_rate > -3 else "주의" if drop_rate > -5 else "기회"
                    self.csv.add_price_record({
                        'code': code,
                        'name': etf['name'],
                        'current_price': price_data['current_price'],
                        'high_52w': high_52w,
                        'low_52w': price_data['low_52w'],
                        'prev_close': price_data['prev_close'],
                        'drop_rate': drop_rate,
                        'status': status
                    })
            
            # 잔고 조회
            balance = self.strategy.api.get_balance()
            
            # 디스코드 전송
            self.discord.send_morning_report(etf_prices, balance)
            
            print("   ✅ 완료")
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            self.discord.send_system_error(str(e))
    
    def check_regular_buy(self):
        """정기 매수 체크 및 실행"""
        
        try:
            # 주말 체크
            if datetime.now().weekday() >= 5:
                return
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📅 정기 매수일 체크 중...")
            
            if self.strategy.check_monthly_buy_day():
                print("   ✅ 오늘은 정기 매수일입니다!")
                
                success = self.strategy.execute_regular_buy()
                
                if success:
                    # 포트폴리오 업데이트
                    time.sleep(10)  # 체결 대기
                    self.strategy.update_portfolio_status()
                
            else:
                buy_day = self.strategy.strategy['buy_day']
                print(f"   ℹ️  정기 매수일이 아닙니다. (매달 {buy_day}일)")
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            self.discord.send_system_error(str(e))
    
    def check_dip_buy(self):
        """하락 매수 기회 체크"""
        
        try:
            # 주말 체크
            if datetime.now().weekday() >= 5:
                return
            
            # 장 시간 체크 (09:00 ~ 15:30)
            now = datetime.now()
            if not (9 <= now.hour < 15 or (now.hour == 15 and now.minute <= 30)):
                return
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📉 하락 매수 기회 체크 중...")
            
            opportunities = self.strategy.check_dip_opportunity()
            
            if opportunities:
                print(f"   🚨 {len(opportunities)}개 종목 하락!")
                
                success = self.strategy.execute_dip_buy(opportunities)
                
                if success:
                    # 포트폴리오 업데이트
                    time.sleep(10)
                    self.strategy.update_portfolio_status()
            else:
                print("   ✅ 매수 기회 없음")
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
    
    def weekly_report(self):
        """주간 리포트"""
        
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📊 주간 리포트 생성 중...")
            
            # 포트폴리오 현황
            portfolio_stats = self.strategy.get_portfolio_summary()
            
            if not portfolio_stats:
                print("   ⚠️  포트폴리오 데이터 없음")
                return
            
            # 주간 거래 요약
            week_ago = datetime.now() - timedelta(days=7)
            trades = self.csv.get_trade_history(start_date=week_ago)
            
            trades_summary = {
                'regular_count': sum(1 for t in trades if t['구분'] == '정기'),
                'dip_count': sum(1 for t in trades if t['구분'] == '기회'),
                'total_invested': sum(float(t['총금액']) for t in trades)
            }
            
            # 디스코드 전송
            self.discord.send_weekly_report(portfolio_stats, trades_summary)
            
            # CSV 리포트 생성
            report_path = self.csv.export_weekly_report()
            
            print(f"   ✅ 완료: {report_path}")
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            self.discord.send_system_error(str(e))
    
    def check_monthly_report(self):
        """월간 리포트 (매월 1일)"""
        
        try:
            # 매월 1일인지 확인
            if datetime.now().day != 1:
                return
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📊 월간 리포트 생성 중...")
            
            year_month = datetime.now().strftime('%Y-%m')
            
            # 월간 거래 내역
            month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
            trades = self.csv.get_trade_history(start_date=month_start)
            
            regular_buy = sum(float(t['총금액']) for t in trades if t['구분'] == '정기')
            dip_buy = sum(float(t['총금액']) for t in trades if t['구분'] == '기회')
            
            # 포트폴리오 현황
            portfolio_stats = self.strategy.get_portfolio_summary()
            
            if not portfolio_stats:
                print("   ⚠️  포트폴리오 데이터 없음")
                return
            
            # 월간 데이터
            monthly_data = {
                'year_month': year_month,
                'regular_buy': regular_buy,
                'dip_buy': dip_buy,
                'monthly_total': regular_buy + dip_buy,
                'cumulative_invest': portfolio_stats['total_invest'],
                'month_end_eval': portfolio_stats['total_eval'],
                'monthly_return': portfolio_stats['total_profit_rate'],  # 간이 계산
                'cumulative_return': portfolio_stats['total_profit_rate'],
                'goal_progress': (portfolio_stats['total_profit_rate'] / 12) * 100  # 12% 목표 기준
            }
            
            # CSV 저장
            self.csv.add_monthly_stat(monthly_data)
            
            # 디스코드 전송
            self.discord.send_monthly_report(monthly_data)
            
            # CSV 리포트 생성
            report_path = self.csv.export_monthly_report(year_month)
            
            print(f"   ✅ 완료: {report_path}")
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            self.discord.send_system_error(str(e))
    
    def update_portfolio(self):
        """포트폴리오 상태 업데이트"""
        
        try:
            # 주말 체크
            if datetime.now().weekday() >= 5:
                return
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📊 포트폴리오 업데이트 중...")
            
            success = self.strategy.update_portfolio_status()
            
            if success:
                print("   ✅ 완료")
            else:
                print("   ⚠️  업데이트 실패")
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
    
    def run(self):
        """메인 루프 실행"""
        
        print("="*70)
        print("🔄 스케줄러 실행 중... (Ctrl+C로 종료)")
        print("="*70 + "\n")
        
        # 다음 실행 예정 출력
        self._print_next_runs()
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("🛑 시스템 종료")
            print("="*70)
            
            # 종료 알림
            self.discord.send_message("시스템이 수동으로 종료되었습니다.")
            
        except Exception as e:
            print(f"\n❌ 치명적 오류: {e}")
            traceback.print_exc()
            
            # 에러 알림
            self.discord.send_system_error(f"치명적 오류: {e}")
    
    def _print_next_runs(self):
        """다음 실행 예정 시간 출력"""
        
        jobs = schedule.get_jobs()
        
        if not jobs:
            return
        
        print("📅 다음 실행 예정:")
        print("-" * 70)
        
        for job in jobs[:5]:  # 최대 5개만
            next_run = job.next_run
            if next_run:
                time_str = next_run.strftime('%Y-%m-%d %H:%M:%S')
                job_func = job.job_func.__name__
                print(f"   {time_str} - {job_func}")
        
        print("-" * 70 + "\n")


def main():
    """메인 실행 함수"""
    
    # 인자 처리
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            # 테스트 모드
            print("🧪 테스트 모드")
            investor = ETFAutoInvestor()
            
            print("\n테스트 실행할 기능을 선택하세요:")
            print("1. 아침 리포트")
            print("2. 정기 매수 체크")
            print("3. 하락 매수 체크")
            print("4. 주간 리포트")
            print("5. 포트폴리오 업데이트")
            
            choice = input("\n선택 (1-5): ")
            
            if choice == "1":
                investor.morning_report()
            elif choice == "2":
                investor.check_regular_buy()
            elif choice == "3":
                investor.check_dip_buy()
            elif choice == "4":
                investor.weekly_report()
            elif choice == "5":
                investor.update_portfolio()
            else:
                print("잘못된 선택입니다.")
            
            return
        
        elif command == "status":
            # 상태 확인 모드
            print("📊 시스템 상태 확인")
            investor = ETFAutoInvestor()
            
            # 계좌 상태
            investor.strategy.api.check_account_status()
            
            # 포트폴리오 요약
            summary = investor.strategy.get_portfolio_summary()
            if summary:
                print("\n" + "="*70)
                print("💼 포트폴리오 현황")
                print("="*70)
                print(f"총 투자금: {summary['total_invest']:,.0f}원")
                print(f"총 평가금: {summary['total_eval']:,.0f}원")
                print(f"평가손익: {summary['total_profit_loss']:+,.0f}원")
                print(f"수익률: {summary['total_profit_rate']:+.2f}%")
                print(f"보유종목: {summary['stock_count']}개")
                print("="*70)
            
            return
        
        elif command == "help":
            print("""
ETF 자동투자 시스템 사용법

python main.py          - 정상 실행 (스케줄러 시작)
python main.py test     - 테스트 모드 (기능별 테스트)
python main.py status   - 상태 확인 모드
python main.py help     - 도움말
            """)
            return
    
    # 정상 실행
    investor = ETFAutoInvestor()
    investor.run()


if __name__ == "__main__":
    main()