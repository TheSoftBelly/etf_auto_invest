from datetime import datetime, timedelta
import pandas as pd
from csv_manager import CSVManager
from chart_generator import ChartGenerator
from discord_bot import DiscordBot

class ReportGenerator:
    """시각화 리포트 생성기"""
    
    def __init__(self, discord_webhook_url):
        self.csv = CSVManager()
        self.chart = ChartGenerator()
        self.discord = DiscordBot(discord_webhook_url)
    
    def generate_weekly_visual_report(self):
        """주간 시각화 리포트 생성 및 전송"""
        
        print("\n📊 주간 시각화 리포트 생성 중...")
        
        try:
            # 1. 포트폴리오 데이터 수집
            portfolio = self.csv.get_portfolio()
            
            if not portfolio:
                print("⚠️  포트폴리오 데이터 없음")
                return False
            
            # 2. 차트 데이터 준비
            portfolio_chart_data = []
            returns_chart_data = []
            
            for p in portfolio:
                portfolio_chart_data.append({
                    'name': p['ETF명'],
                    'value': float(p['평가금액'])
                })
                
                returns_chart_data.append({
                    'name': p['ETF명'],
                    'return': float(p['수익률(%)'])
                })
            
            # 3. 차트 생성
            charts = []
            
            # 포트폴리오 구성 원형 차트
            chart1 = self.chart.create_portfolio_pie_chart(portfolio_chart_data)
            charts.append(chart1)
            print(f"  ✅ 포트폴리오 차트: {chart1}")
            
            # ETF별 수익률 막대 차트
            chart2 = self.chart.create_return_bar_chart(returns_chart_data)
            charts.append(chart2)
            print(f"  ✅ 수익률 차트: {chart2}")
            
            # 4. 요약 정보
            stats = self.csv.calculate_portfolio_stats()
            
            summary_text = (
                f"**💰 포트폴리오 현황**\n"
                f"총 투자금: {stats['total_invest']:,.0f}원\n"
                f"총 평가금: {stats['total_eval']:,.0f}원\n"
                f"평가손익: {stats['total_profit_loss']:+,.0f}원\n"
                f"수익률: {stats['total_profit_rate']:+.2f}%\n"
            )
            
            # 5. 디스코드 전송
            self.discord.send_chart_with_embed(
                "📊 주간 투자 리포트",
                summary_text,
                chart1,
                color=0x3498db
            )
            
            # 수익률 차트 전송
            self.discord.send_chart_with_embed(
                "📈 ETF별 수익률",
                "종목별 수익률 비교",
                chart2,
                color=0x2ecc71 if stats['total_profit_rate'] > 0 else 0xe74c3c
            )
            
            print("✅ 주간 시각화 리포트 전송 완료")
            return True
            
        except Exception as e:
            print(f"❌ 주간 리포트 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_monthly_visual_report(self, year_month=None):
        """월간 시각화 리포트 생성 및 전송"""
        
        if not year_month:
            year_month = datetime.now().strftime('%Y-%m')
        
        print(f"\n📊 {year_month} 월간 시각화 리포트 생성 중...")
        
        try:
            # 1. 월간 통계 조회
            monthly_stats = self.csv.get_monthly_stats()
            
            if not monthly_stats:
                print("⚠️  월간 통계 데이터 없음")
                # 간단한 현재 포트폴리오만 전송
                return self.generate_weekly_visual_report()
            
            # 2. 월별 투자 차트 데이터
            monthly_chart_data = []
            for stat in monthly_stats[-6:]:  # 최근 6개월
                monthly_chart_data.append({
                    'month': stat['년월'],
                    'regular': float(stat['정기매수액']),
                    'dip': float(stat['기회매수액'])
                })
            
            # 3. 누적 수익률 차트 데이터
            cumulative_data = []
            for stat in monthly_stats:
                cumulative_data.append({
                    'date': f"{stat['년월']}-01",
                    'total_value': float(stat['월말평가액']),
                    'invested': float(stat['누적투자금'])
                })
            
            # 4. 현재 포트폴리오
            portfolio = self.csv.get_portfolio()
            portfolio_data = [
                {'name': p['ETF명'], 'value': float(p['평가금액'])}
                for p in portfolio
            ]
            
            returns_data = [
                {'name': p['ETF명'], 'return': float(p['수익률(%)'])}
                for p in portfolio
            ]
            
            # 5. 차트 생성
            charts = []
            
            # 월별 투자 차트
            if monthly_chart_data:
                chart1 = self.chart.create_monthly_investment_chart(monthly_chart_data)
                charts.append(chart1)
                print(f"  ✅ 월별 투자 차트: {chart1}")
            
            # 누적 수익률 차트
            if len(cumulative_data) > 1:
                chart2 = self.chart.create_cumulative_return_chart(cumulative_data)
                charts.append(chart2)
                print(f"  ✅ 누적 수익률 차트: {chart2}")
            
            # 종합 대시보드
            dashboard_data = {
                'portfolio': portfolio_data,
                'returns': returns_data,
                'monthly': monthly_chart_data,
                'categories': []  # 카테고리 데이터가 있으면 추가
            }
            
            chart3 = self.chart.create_dashboard(dashboard_data)
            charts.append(chart3)
            print(f"  ✅ 종합 대시보드: {chart3}")
            
            # 6. 요약 정보
            latest_stat = monthly_stats[-1]
            stats = self.csv.calculate_portfolio_stats()
            
            summary_data = {
                'total_invest': stats['total_invest'],
                'total_eval': stats['total_eval'],
                'total_return': stats['total_profit_rate'],
                'best_etf': max(returns_data, key=lambda x: x['return'])['name'] if returns_data else '-',
                'period': f"{year_month} 월간"
            }
            
            # 7. 디스코드 전송
            # 대시보드 먼저
            self.discord.send_dashboard_report(chart3, summary_data)
            
            # 상세 차트들
            if len(charts) > 1:
                for i, chart_path in enumerate(charts[:-1], 1):  # 대시보드 제외
                    self.discord.send_chart_with_embed(
                        f"📊 월간 리포트 - 상세 차트 {i}",
                        "",
                        chart_path,
                        color=0x3498db
                    )
            
            print("✅ 월간 시각화 리포트 전송 완료")
            return True
            
        except Exception as e:
            print(f"❌ 월간 리포트 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_portfolio_snapshot(self):
        """현재 포트폴리오 스냅샷 (차트만)"""
        
        print("\n📸 포트폴리오 스냅샷 생성 중...")
        
        try:
            portfolio = self.csv.get_portfolio()
            
            if not portfolio:
                print("⚠️  포트폴리오 데이터 없음")
                return False
            
            # 데이터 준비
            portfolio_data = [
                {'name': p['ETF명'], 'value': float(p['평가금액'])}
                for p in portfolio
            ]
            
            returns_data = [
                {'name': p['ETF명'], 'return': float(p['수익률(%)'])}
                for p in portfolio
            ]
            
            # 차트 생성
            chart1 = self.chart.create_portfolio_pie_chart(portfolio_data)
            chart2 = self.chart.create_return_bar_chart(returns_data)
            
            # 요약 정보
            stats = self.csv.calculate_portfolio_stats()
            
            # 전송
            self.discord.send_chart_with_embed(
                "📊 포트폴리오 현황",
                f"총 평가금: {stats['total_eval']:,.0f}원\n수익률: {stats['total_profit_rate']:+.2f}%",
                chart1,
                color=0x2ecc71 if stats['total_profit_rate'] > 0 else 0xe74c3c
            )
            
            self.discord.send_chart_with_embed(
                "📈 수익률 분석",
                "종목별 수익률 비교",
                chart2,
                color=0x3498db
            )
            
            print("✅ 스냅샷 전송 완료")
            return True
            
        except Exception as e:
            print(f"❌ 스냅샷 생성 실패: {e}")
            return False
    
    def generate_performance_analysis(self):
        """성과 분석 리포트 (심화 차트)"""
        
        print("\n📊 성과 분석 리포트 생성 중...")
        
        try:
            # 가격 히스토리에서 최근 30일 데이터
            price_history_file = self.csv.data_dir / 'price_history.csv'
            
            if not price_history_file.exists():
                print("⚠️  가격 기록 데이터 없음")
                return False
            
            df = pd.read_csv(price_history_file, encoding='utf-8-sig')
            df['날짜'] = pd.to_datetime(df['날짜'])
            
            # 최근 30일
            recent_30d = df[df['날짜'] >= (datetime.now() - timedelta(days=30))]
            
            # ETF별로 하락률 추이 분석
            etf_list = recent_30d['ETF명'].unique()
            
            charts = []
            
            for etf_name in etf_list[:3]:  # 상위 3개만
                etf_data = recent_30d[recent_30d['ETF명'] == etf_name].sort_values('날짜')
                
                if len(etf_data) < 2:
                    continue
                
                # 간단한 라인 차트 (가격 추이)
                import matplotlib.pyplot as plt
                
                fig, ax = plt.subplots(figsize=(12, 6))
                
                dates = etf_data['날짜']
                prices = etf_data['현재가']
                
                ax.plot(dates, prices, marker='o', linewidth=2, markersize=4)
                ax.set_title(f'📈 {etf_name} 가격 추이 (30일)', fontsize=14, weight='bold')
                ax.set_xlabel('날짜')
                ax.set_ylabel('가격 (원)')
                ax.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                filename = f"price_trend_{etf_name}_{datetime.now().strftime('%Y%m%d')}.png"
                filepath = self.chart.output_dir / filename
                plt.savefig(filepath, dpi=300, bbox_inches='tight')
                plt.close()
                
                charts.append(str(filepath))
            
            # 차트 전송
            for chart_path in charts:
                self.discord.send_chart_with_embed(
                    "📈 가격 추이 분석",
                    "최근 30일 가격 변동",
                    chart_path,
                    color=0x9b59b6
                )
            
            print("✅ 성과 분석 완료")
            return True
            
        except Exception as e:
            print(f"❌ 성과 분석 실패: {e}")
            import traceback
            traceback.print_exc()
            return False


# 테스트 코드
if __name__ == "__main__":
    import yaml
    
    with open('config.yaml', encoding='UTF-8') as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
    
    report_gen = ReportGenerator(cfg['DISCORD_WEBHOOK_URL'])
    
    print("=" * 70)
    print("🧪 ReportGenerator 테스트")
    print("=" * 70)
    
    print("\n테스트할 리포트를 선택하세요:")
    print("1. 포트폴리오 스냅샷")
    print("2. 주간 시각화 리포트")
    print("3. 월간 시각화 리포트")
    print("4. 성과 분석")
    
    choice = input("\n선택 (1-4): ")
    
    if choice == "1":
        report_gen.generate_portfolio_snapshot()
    elif choice == "2":
        report_gen.generate_weekly_visual_report()
    elif choice == "3":
        report_gen.generate_monthly_visual_report()
    elif choice == "4":
        report_gen.generate_performance_analysis()
    else:
        print("잘못된 선택입니다.")