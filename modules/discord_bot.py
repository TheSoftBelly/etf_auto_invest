import requests
import json
from datetime import datetime
import time
from pathlib import Path

class DiscordBot:
    """디스코드 Webhook 알림 시스템"""
    
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.rate_limit_delay = 1  # 메시지 간 1초 딜레이 (rate limit 방지)
    
    def _send_webhook(self, data, files=None):
        """Webhook 전송 (내부 함수)"""
        try:
            if files:
                # 파일 첨부가 있는 경우
                response = requests.post(
                    self.webhook_url,
                    data={'payload_json': json.dumps(data)},
                    files=files
                )
            else:
                # 일반 메시지
                response = requests.post(
                    self.webhook_url,
                    data=json.dumps(data),
                    headers={"Content-Type": "application/json"}
                )
            
            if response.status_code in [200, 204]:
                return True
            elif response.status_code == 429:
                # Rate limit 걸림
                retry_after = response.json().get('retry_after', 5)
                print(f"⚠️  Rate limit 걸림. {retry_after}초 후 재시도...")
                time.sleep(retry_after)
                return self._send_webhook(data, files)
            else:
                print(f"❌ Discord 전송 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Discord 전송 에러: {e}")
            return False
    
    def send_message(self, message):
        """단순 텍스트 메시지 전송"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            "content": f"[{now}] {message}"
        }
        
        result = self._send_webhook(data)
        time.sleep(self.rate_limit_delay)
        return result
    
    def send_embed(self, title, description, color=0x3498db, fields=None, footer=None):
        """임베드 메시지 전송 (예쁜 박스 형태)
        
        Args:
            title: 제목
            description: 설명
            color: 색상 (hex)
                - 0x2ecc71: 초록 (성공)
                - 0xe74c3c: 빨강 (실패/경고)
                - 0x3498db: 파랑 (정보)
                - 0xf39c12: 주황 (알림)
            fields: [{name: "", value: "", inline: True/False}, ...]
            footer: 하단 텍스트
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if fields:
            embed["fields"] = fields
        
        if footer:
            embed["footer"] = {"text": footer}
        else:
            embed["footer"] = {"text": f"ETF 자동투자 시스템 • {now}"}
        
        data = {"embeds": [embed]}
        
        result = self._send_webhook(data)
        time.sleep(self.rate_limit_delay)
        return result
    
    def send_morning_report(self, etf_prices, balance):
        """아침 시장 리포트"""
        
        # ETF 정보 필드 생성
        fields = []
        for etf in etf_prices:
            status_emoji = "✅" if etf['drop_rate'] > -3 else "⚠️" if etf['drop_rate'] > -5 else "🚨"
            
            fields.append({
                "name": f"{status_emoji} {etf['name']}",
                "value": (
                    f"**현재가:** {etf['current_price']:,}원\n"
                    f"**52주 대비:** {etf['drop_rate']:+.2f}%\n"
                    f"**전일대비:** {etf.get('change', 0):+,}원 ({etf.get('change_rate', 0):+.2f}%)"
                ),
                "inline": True
            })
        
        # 잔고 정보
        fields.append({
            "name": "💰 주문가능 현금",
            "value": f"**{balance:,}원**",
            "inline": False
        })
        
        return self.send_embed(
            title="🌅 굿모닝! 오늘의 ETF 현황",
            description="장 시작 전 포트폴리오 상태를 확인하세요.",
            color=0x3498db,
            fields=fields
        )
    
    def send_dip_alert(self, opportunity):
        """하락 매수 기회 알림
        
        Args:
            opportunity: {
                'code': 'ETF코드',
                'name': 'ETF명',
                'current_price': 현재가,
                'high_52w': 52주최고가,
                'drop_rate': 하락률,
                'recommended_buy': {추천 매수 정보}
            }
        """
        
        fields = [
            {
                "name": "📊 현재 상황",
                "value": (
                    f"**현재가:** {opportunity['current_price']:,}원\n"
                    f"**52주 최고가:** {opportunity['high_52w']:,}원\n"
                    f"**하락률:** {opportunity['drop_rate']:.2f}%"
                ),
                "inline": True
            }
        ]
        
        # 추천 매수 정보가 있으면 추가
        if 'recommended_buy' in opportunity:
            rec = opportunity['recommended_buy']
            fields.append({
                "name": "💰 추천 매수",
                "value": (
                    f"**수량:** {rec['quantity']}주\n"
                    f"**예상금액:** {rec['total_amount']:,}원\n"
                    f"**구분:** {rec['type']}"
                ),
                "inline": True
            })
        
        return self.send_embed(
            title=f"🚨 매수 기회 발생! - {opportunity['name']}",
            description=(
                f"**{opportunity['name']}**이(가) 52주 최고가 대비 "
                f"**{opportunity['drop_rate']:.2f}%** 하락했습니다.\n\n"
                "⏰ 24시간 이내 매수를 권장합니다."
            ),
            color=0xe74c3c,
            fields=fields
        )
    
    def send_trade_success(self, trade_info):
        """매매 체결 성공 알림
        
        Args:
            trade_info: {
                'type': '매수' or '매도',
                'code': 'ETF코드',
                'name': 'ETF명',
                'price': 체결가,
                'quantity': 수량,
                'total_amount': 총금액,
                'order_no': 주문번호,
                'category': '정기' or '기회'
            }
        """
        
        emoji = "✅" if trade_info['type'] == '매수' else "📤"
        color = 0x2ecc71 if trade_info['type'] == '매수' else 0x95a5a6
        
        fields = [
            {
                "name": "📋 거래 내역",
                "value": (
                    f"**종목:** {trade_info['name']}\n"
                    f"**종목코드:** {trade_info['code']}\n"
                    f"**구분:** {trade_info.get('category', '-')}"
                ),
                "inline": True
            },
            {
                "name": "💵 체결 정보",
                "value": (
                    f"**체결가:** {trade_info['price']:,}원\n"
                    f"**수량:** {trade_info['quantity']}주\n"
                    f"**총금액:** {trade_info['total_amount']:,}원"
                ),
                "inline": True
            },
            {
                "name": "📝 주문번호",
                "value": f"`{trade_info.get('order_no', '-')}`",
                "inline": False
            }
        ]
        
        return self.send_embed(
            title=f"{emoji} {trade_info['type']} 체결 완료!",
            description=f"**{trade_info['name']}** {trade_info['type']}이 성공적으로 체결되었습니다.",
            color=color,
            fields=fields
        )
    
    def send_trade_failure(self, trade_info, error_msg):
        """매매 체결 실패 알림"""
        
        fields = [
            {
                "name": "📋 시도한 거래",
                "value": (
                    f"**종목:** {trade_info['name']}\n"
                    f"**수량:** {trade_info['quantity']}주\n"
                    f"**예상금액:** {trade_info.get('total_amount', 0):,}원"
                ),
                "inline": True
            },
            {
                "name": "❌ 실패 사유",
                "value": f"```{error_msg}```",
                "inline": False
            }
        ]
        
        return self.send_embed(
            title=f"❌ {trade_info['type']} 주문 실패",
            description="주문이 실패했습니다. 계좌 상태를 확인해주세요.",
            color=0xe74c3c,
            fields=fields
        )
    
    def send_weekly_report(self, portfolio_stats, trades_summary):
        """주간 리포트
        
        Args:
            portfolio_stats: {
                'total_invest': 총투자금,
                'total_eval': 총평가금액,
                'total_profit_loss': 평가손익,
                'total_profit_rate': 수익률,
                'stocks': [{종목정보}, ...]
            }
            trades_summary: {
                'regular_count': 정기매수 횟수,
                'dip_count': 기회매수 횟수,
                'total_invested': 주간 투자금액
            }
        """
        
        # 수익률에 따른 색상
        profit_rate = portfolio_stats['total_profit_rate']
        if profit_rate >= 5:
            color = 0x2ecc71  # 초록
        elif profit_rate >= 0:
            color = 0x3498db  # 파랑
        else:
            color = 0xe74c3c  # 빨강
        
        # 전체 요약
        fields = [
            {
                "name": "💰 포트폴리오 현황",
                "value": (
                    f"**총 투자금액:** {portfolio_stats['total_invest']:,.0f}원\n"
                    f"**총 평가금액:** {portfolio_stats['total_eval']:,.0f}원\n"
                    f"**평가손익:** {portfolio_stats['total_profit_loss']:+,.0f}원\n"
                    f"**수익률:** {profit_rate:+.2f}%"
                ),
                "inline": False
            }
        ]
        
        # 주간 활동
        if trades_summary:
            fields.append({
                "name": "📊 이번 주 활동",
                "value": (
                    f"**정기매수:** {trades_summary.get('regular_count', 0)}회\n"
                    f"**기회매수:** {trades_summary.get('dip_count', 0)}회\n"
                    f"**투자금액:** {trades_summary.get('total_invested', 0):,.0f}원"
                ),
                "inline": False
            })
        
        # 보유 종목 (상위 3개)
        if portfolio_stats.get('stocks'):
            top_stocks = sorted(
                portfolio_stats['stocks'], 
                key=lambda x: x['profit_rate'], 
                reverse=True
            )[:3]
            
            stock_text = ""
            for stock in top_stocks:
                emoji = "📈" if stock['profit_rate'] > 0 else "📉"
                stock_text += (
                    f"{emoji} **{stock['name']}**\n"
                    f"   수익률: {stock['profit_rate']:+.2f}% "
                    f"({stock['profit_loss']:+,.0f}원)\n"
                )
            
            fields.append({
                "name": "🏆 보유 종목 (수익률 순)",
                "value": stock_text,
                "inline": False
            })
        
        return self.send_embed(
            title="📊 주간 투자 리포트",
            description=f"한 주간의 투자 성과를 확인하세요.",
            color=color,
            fields=fields
        )
    
    def send_monthly_report(self, monthly_data):
        """월간 리포트
        
        Args:
            monthly_data: {
                'year_month': '2025-11',
                'regular_buy': 정기매수액,
                'dip_buy': 기회매수액,
                'monthly_total': 월합계,
                'cumulative_invest': 누적투자금,
                'month_end_eval': 월말평가액,
                'monthly_return': 월간수익률,
                'cumulative_return': 누적수익률,
                'goal_progress': 목표대비 진행률
            }
        """
        
        # 수익률에 따른 색상
        monthly_return = monthly_data['monthly_return']
        if monthly_return >= 3:
            color = 0x2ecc71
        elif monthly_return >= 0:
            color = 0x3498db
        else:
            color = 0xe74c3c
        
        fields = [
            {
                "name": "💸 월간 투자 내역",
                "value": (
                    f"**정기 매수:** {monthly_data['regular_buy']:,.0f}원\n"
                    f"**기회 매수:** {monthly_data['dip_buy']:,.0f}원\n"
                    f"**월간 합계:** {monthly_data['monthly_total']:,.0f}원"
                ),
                "inline": True
            },
            {
                "name": "📈 성과 현황",
                "value": (
                    f"**누적 투자금:** {monthly_data['cumulative_invest']:,.0f}원\n"
                    f"**월말 평가액:** {monthly_data['month_end_eval']:,.0f}원\n"
                    f"**월간 수익률:** {monthly_return:+.2f}%\n"
                    f"**누적 수익률:** {monthly_data['cumulative_return']:+.2f}%"
                ),
                "inline": True
            }
        ]
        
        # 목표 달성률
        if 'goal_progress' in monthly_data:
            progress = monthly_data['goal_progress']
            progress_bar = self._create_progress_bar(progress)
            
            fields.append({
                "name": "🎯 연간 목표 달성률 (12-17%)",
                "value": f"{progress_bar}\n**{progress:.1f}%** 달성",
                "inline": False
            })
        
        return self.send_embed(
            title=f"📊 {monthly_data['year_month']} 월간 투자 리포트",
            description="한 달간의 투자 성과를 정리했습니다.",
            color=color,
            fields=fields
        )
    
    def send_balance_warning(self, required_amount, current_balance):
        """잔고 부족 경고"""
        
        shortage = required_amount - current_balance
        
        fields = [
            {
                "name": "💵 현재 상황",
                "value": (
                    f"**필요 금액:** {required_amount:,.0f}원\n"
                    f"**현재 잔고:** {current_balance:,.0f}원\n"
                    f"**부족 금액:** {shortage:,.0f}원"
                ),
                "inline": False
            }
        ]
        
        return self.send_embed(
            title="⚠️ 잔고 부족 경고",
            description=(
                "정기 매수를 위한 잔고가 부족합니다.\n"
                "입금 후 수동으로 매수를 진행해주세요."
            ),
            color=0xf39c12,
            fields=fields
        )
    
    def send_system_start(self):
        """시스템 시작 알림"""
        return self.send_embed(
            title="🚀 ETF 자동투자 시스템 시작",
            description=(
                "시스템이 성공적으로 시작되었습니다.\n"
                "가격 모니터링 및 자동 알림이 활성화되었습니다."
            ),
            color=0x2ecc71
        )
    
    def send_system_error(self, error_message):
        """시스템 에러 알림"""
        fields = [
            {
                "name": "❌ 에러 내용",
                "value": f"```{error_message}```",
                "inline": False
            }
        ]
        
        return self.send_embed(
            title="⚠️ 시스템 오류 발생",
            description="시스템에 오류가 발생했습니다. 확인이 필요합니다.",
            color=0xe74c3c,
            fields=fields
        )
    
    def send_chart_with_embed(self, title, description, chart_path, color=0x3498db):
        """차트 이미지와 함께 임베드 메시지 전송
        
        Args:
            title: 제목
            description: 설명
            chart_path: 차트 이미지 파일 경로
            color: 임베드 색상
        
        Returns:
            bool: 전송 성공 여부
        """
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 임베드 데이터
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "image": {
                "url": f"attachment://{Path(chart_path).name}"
            },
            "footer": {
                "text": f"ETF 자동투자 시스템 • {now}"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        data = {"embeds": [embed]}
        
        # 파일 첨부
        try:
            with open(chart_path, 'rb') as f:
                files = {
                    'file': (Path(chart_path).name, f, 'image/png')
                }
                result = self._send_webhook(data, files)
            
            time.sleep(self.rate_limit_delay)
            return result
            
        except Exception as e:
            print(f"❌ 차트 전송 실패: {e}")
            return False
    
    def send_multiple_charts(self, title, description, chart_paths, color=0x3498db):
        """여러 차트 이미지 전송
        
        Args:
            title: 제목
            description: 설명
            chart_paths: 차트 이미지 파일 경로 리스트
            color: 임베드 색상
        """
        
        # 첫 번째 차트는 임베드와 함께
        if len(chart_paths) > 0:
            self.send_chart_with_embed(title, description, chart_paths[0], color)
        
        # 나머지 차트는 순차 전송
        for i, chart_path in enumerate(chart_paths[1:], 2):
            self.send_chart_with_embed(
                f"{title} ({i}/{len(chart_paths)})",
                "",
                chart_path,
                color
            )
            time.sleep(1)  # Rate limit 방지
    
    def send_dashboard_report(self, chart_path, summary_data):
        """종합 대시보드 리포트 전송
        
        Args:
            chart_path: 대시보드 이미지 경로
            summary_data: {
                'total_invest': 총투자금,
                'total_eval': 총평가금,
                'total_return': 수익률,
                'best_etf': 최고수익ETF,
                'period': '기간'
            }
        """
        
        # 수익률에 따른 색상
        total_return = summary_data.get('total_return', 0)
        if total_return >= 5:
            color = 0x2ecc71  # 초록
        elif total_return >= 0:
            color = 0x3498db  # 파랑
        else:
            color = 0xe74c3c  # 빨강
        
        description = (
            f"**📊 {summary_data.get('period', '종합')} 투자 리포트**\n\n"
            f"💰 총 투자금: {summary_data.get('total_invest', 0):,.0f}원\n"
            f"📈 총 평가금: {summary_data.get('total_eval', 0):,.0f}원\n"
            f"💵 수익률: {total_return:+.2f}%\n"
            f"🏆 최고수익: {summary_data.get('best_etf', '-')}"
        )
        
        return self.send_chart_with_embed(
            "📊 투자 대시보드",
            description,
            chart_path,
            color
        )


# 테스트 코드
if __name__ == "__main__":
    # config.yaml에서 webhook URL 읽기
    try:
        import yaml
        with open('config.yaml', encoding='UTF-8') as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
        
        bot = DiscordBot(cfg['DISCORD_WEBHOOK_URL'])
        
        print("=== Discord Bot 테스트 ===\n")
        
        # 1. 단순 메시지
        print("1. 단순 메시지 전송...")
        bot.send_message("테스트 메시지입니다! 👋")
        time.sleep(2)
        
        # 2. 시스템 시작
        print("2. 시스템 시작 알림...")
        bot.send_system_start()
        time.sleep(2)
        
        # 3. 아침 리포트
        print("3. 아침 리포트 전송...")
        etf_prices = [
            {
                'name': 'TIGER 미국나스닥100',
                'current_price': 159215,
                'drop_rate': -0.47,
                'change': -750,
                'change_rate': -0.47
            },
            {
                'name': 'ACE 미국빅테크TOP7',
                'current_price': 21756,
                'drop_rate': -1.14,
                'change': -250,
                'change_rate': -1.14
            }
        ]
        bot.send_morning_report(etf_prices, 1500000)
        time.sleep(2)
        
        # 4. 하락 알림
        print("4. 하락 매수 기회 알림...")
        opportunity = {
            'code': '133690',
            'name': 'TIGER 미국나스닥100',
            'current_price': 151250,
            'high_52w': 159960,
            'drop_rate': -5.45,
            'recommended_buy': {
                'quantity': 1,
                'total_amount': 151250,
                'type': '기회매수'
            }
        }
        bot.send_dip_alert(opportunity)
        time.sleep(2)
        
        # 5. 매수 성공
        print("5. 매수 체결 알림...")
        trade_info = {
            'type': '매수',
            'code': '133690',
            'name': 'TIGER 미국나스닥100',
            'price': 151250,
            'quantity': 1,
            'total_amount': 151250,
            'order_no': '1234567890',
            'category': '기회매수'
        }
        bot.send_trade_success(trade_info)
        
        print("\n✅ 모든 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")