import yaml
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .kis_api import KISApi
from .portfolio_allocator import PortfolioAllocator
from .csv_manager import CSVManager
from .discord_bot import DiscordBot

class TradingStrategy:
    """매매 전략 실행 엔진"""
    
    def __init__(self, config_path='config.yaml'):
        with open(config_path, encoding='UTF-8') as f:
            self.cfg = yaml.load(f, Loader=yaml.FullLoader)
        
        self.strategy = self.cfg['STRATEGY']
        self.auto_trade = self.cfg.get('ADVANCED', {}).get('auto_trade', False)
        
        # 모듈 초기화
        self.api = KISApi(config_path)
        self.allocator = PortfolioAllocator(config_path)
        self.csv = CSVManager()
        self.discord = DiscordBot(self.cfg['DISCORD_WEBHOOK_URL'])
        
        # 52주 최고가 캐시
        self.high_52w_cache = {}
        self._update_52w_high()
        
        print(f"✅ TradingStrategy 초기화 완료")
        print(f"   자동매매 모드: {'ON' if self.auto_trade else 'OFF (알림만)'}")
    
    def _update_52w_high(self):
        """52주 최고가 업데이트"""
        for etf in self.allocator.active_etfs:
            code = etf['code']
            price_data = self.api.get_domestic_etf_price(code)
            if price_data:
                self.high_52w_cache[code] = price_data['high_52w']
    
    def check_monthly_buy_day(self) -> bool:
        """정기 매수일 확인"""
        today = datetime.now()
        buy_day = self.strategy['buy_day']
        
        return today.day == buy_day
    
    def execute_regular_buy(self) -> bool:
        """정기 매수 실행"""
        
        print("\n" + "="*70)
        print("📅 정기 매수 실행")
        print("="*70)
        
        # 1. 잔고 확인
        balance = self.api.get_balance()
        required = self.strategy['monthly_regular_amount']
        
        if balance < required:
            self.discord.send_balance_warning(required, balance)
            print(f"❌ 잔고 부족: {balance:,}원 (필요: {required:,}원)")
            return False
        
        print(f"✅ 잔고 확인: {balance:,}원")
        
        # 2. 현재가 조회
        current_prices = self._get_current_prices()
        
        if not current_prices:
            print("❌ 가격 조회 실패")
            return False
        
        # 3. 배분 계획 수립
        allocations = self.allocator.calculate_allocation(required, mode='REGULAR')
        buy_orders = self.allocator.calculate_buy_quantities(allocations, current_prices)
        
        # 4. 배분 계획 출력
        self.allocator.print_allocation_plan(buy_orders)
        
        # 5. 실제 매수 실행
        if self.auto_trade:
            return self._execute_buy_orders(buy_orders, 'REGULAR')
        else:
            # 알림만
            self._send_buy_plan_alert(buy_orders, 'REGULAR')
            print("💡 알림만 모드: 수동으로 매수해주세요.")
            return True
    
    def check_dip_opportunity(self) -> List[Dict]:
        """하락 매수 기회 체크"""
        
        opportunities = []
        threshold = self.strategy['dip_threshold']
        
        for etf in self.allocator.active_etfs:
            code = etf['code']
            name = etf['name']
            
            price_data = self.api.get_domestic_etf_price(code)
            if not price_data:
                continue
            
            current_price = price_data['current_price']
            high_52w = self.high_52w_cache.get(code, price_data['high_52w'])
            
            drop_rate = ((current_price - high_52w) / high_52w) * 100
            
            if drop_rate <= threshold:
                opportunities.append({
                    'code': code,
                    'name': name,
                    'current_price': current_price,
                    'high_52w': high_52w,
                    'drop_rate': drop_rate,
                    'category': etf.get('category', 'UNKNOWN')
                })
                
                print(f"🚨 매수 기회: {name} ({drop_rate:.2f}%)")
        
        return opportunities
    
    def execute_dip_buy(self, opportunities: List[Dict]) -> bool:
        """하락 매수 실행"""
        
        if not opportunities:
            print("매수 기회가 없습니다.")
            return False
        
        print("\n" + "="*70)
        print("🚨 하락 매수 실행")
        print("="*70)
        
        # 1. 잔고 확인
        balance = self.api.get_balance()
        dip_amount = self.strategy['dip_buy_amount']
        
        if balance < dip_amount:
            print(f"❌ 잔고 부족: {balance:,}원 (필요: {dip_amount:,}원)")
            return False
        
        print(f"✅ 잔고 확인: {balance:,}원")
        
        # 2. 하락 종목만 필터링해서 배분
        dip_codes = [opp['code'] for opp in opportunities]
        
        # 임시로 하락 종목만 활성화
        original_etfs = self.allocator.active_etfs
        self.allocator.active_etfs = [
            etf for etf in original_etfs 
            if etf['code'] in dip_codes
        ]
        
        # 3. 배분 계획 수립
        allocations = self.allocator.calculate_allocation(dip_amount, mode='DIP')
        
        current_prices = {opp['code']: opp['current_price'] for opp in opportunities}
        buy_orders = self.allocator.calculate_buy_quantities(allocations, current_prices)
        
        # 원래 ETF 리스트로 복원
        self.allocator.active_etfs = original_etfs
        
        # 4. 배분 계획 출력
        self.allocator.print_allocation_plan(buy_orders)
        
        # 5. 실제 매수 실행
        if self.auto_trade:
            return self._execute_buy_orders(buy_orders, 'DIP')
        else:
            # 알림만
            self._send_buy_plan_alert(buy_orders, 'DIP')
            print("💡 알림만 모드: 수동으로 매수해주세요.")
            
            # 디스코드 하락 알림
            for opp in opportunities:
                rec_order = next((o for o in buy_orders if o['code'] == opp['code']), None)
                if rec_order:
                    opp['recommended_buy'] = {
                        'quantity': rec_order['quantity'],
                        'total_amount': rec_order['actual_amount'],
                        'type': '기회매수'
                    }
                self.discord.send_dip_alert(opp)
            
            return True
    
    def _execute_buy_orders(self, buy_orders: List[Dict], order_type: str) -> bool:
        """실제 매수 주문 실행
        
        Args:
            buy_orders: 매수 주문 리스트
            order_type: 'REGULAR' or 'DIP'
        """
        
        success_count = 0
        fail_count = 0
        
        category_text = "정기매수" if order_type == 'REGULAR' else "기회매수"
        
        print(f"\n💰 {category_text} 주문 실행 중...\n")
        
        for order in buy_orders:
            if order['quantity'] == 0:
                print(f"⏭️  {order['name']}: 수량 0 - 건너뜀")
                continue
            
            print(f"📤 {order['name']}: {order['quantity']}주 매수 시도...")
            
            # API 매수 주문
            result = self.api.buy_order(
                code=order['code'],
                quantity=order['quantity'],
                order_type="01"  # 시장가
            )
            
            if result and result['success']:
                success_count += 1
                
                # CSV 기록
                trade_data = {
                    'type': category_text,
                    'code': order['code'],
                    'name': order['name'],
                    'price': order['current_price'],
                    'quantity': order['quantity'],
                    'total': order['actual_amount'],
                    'fee': 0,
                    'memo': f"{category_text} ({datetime.now().strftime('%Y-%m-%d')})"
                }
                self.csv.add_trade(trade_data)
                
                # Discord 알림
                trade_info = {
                    'type': '매수',
                    'code': order['code'],
                    'name': order['name'],
                    'price': order['current_price'],
                    'quantity': order['quantity'],
                    'total_amount': order['actual_amount'],
                    'order_no': result['order_no'],
                    'category': category_text
                }
                self.discord.send_trade_success(trade_info)
                
                print(f"   ✅ 성공: 주문번호 {result['order_no']}")
                
            else:
                fail_count += 1
                error_msg = result['msg'] if result else "알 수 없는 오류"
                
                # Discord 알림
                trade_info = {
                    'type': '매수',
                    'name': order['name'],
                    'quantity': order['quantity'],
                    'total_amount': order['actual_amount']
                }
                self.discord.send_trade_failure(trade_info, error_msg)
                
                print(f"   ❌ 실패: {error_msg}")
            
            # Rate Limit 방지
            import time
            time.sleep(self.cfg.get('ADVANCED', {}).get('api_delay', 0.5))
        
        print(f"\n📊 매수 결과: 성공 {success_count}개 / 실패 {fail_count}개")
        
        return success_count > 0
    
    def _get_current_prices(self) -> Dict[str, float]:
        """현재가 일괄 조회"""
        prices = {}
        
        for etf in self.allocator.active_etfs:
            code = etf['code']
            price_data = self.api.get_domestic_etf_price(code)
            
            if price_data:
                prices[code] = price_data['current_price']
        
        return prices
    
    def _send_buy_plan_alert(self, buy_orders: List[Dict], order_type: str):
        """매수 계획 알림 (수동 모드용)"""
        
        category = "정기매수" if order_type == 'REGULAR' else "기회매수"
        
        fields = []
        total_amount = 0
        
        for order in buy_orders:
            if order['quantity'] > 0:
                fields.append({
                    "name": f"📊 {order['name']}",
                    "value": (
                        f"**수량:** {order['quantity']}주\n"
                        f"**단가:** {order['current_price']:,}원\n"
                        f"**금액:** {order['actual_amount']:,}원"
                    ),
                    "inline": True
                })
                total_amount += order['actual_amount']
        
        fields.append({
            "name": "💰 총 투자 금액",
            "value": f"**{total_amount:,}원**",
            "inline": False
        })
        
        self.discord.send_embed(
            title=f"📋 {category} 계획",
            description=f"아래 종목을 수동으로 매수해주세요.",
            color=0x3498db,
            fields=fields
        )
    
    def update_portfolio_status(self):
        """포트폴리오 상태 업데이트 (CSV)"""
        
        print("\n📊 포트폴리오 상태 업데이트 중...")
        
        # 1. 계좌 잔고 조회
        balance_info = self.api.get_stock_balance()
        
        if not balance_info:
            print("❌ 잔고 조회 실패")
            return False
        
        # 2. 현재가 조회
        current_prices = self._get_current_prices()
        
        # 3. 포트폴리오 데이터 생성
        portfolio_data = []
        
        for code, stock_info in balance_info['stocks'].items():
            current_price = current_prices.get(code, stock_info['current_price'])
            
            portfolio_data.append({
                'code': code,
                'name': stock_info['name'],
                'quantity': stock_info['quantity'],
                'avg_price': stock_info['avg_price'],
                'current_price': current_price,
                'eval_amt': stock_info['eval_amt'],
                'invest_amt': stock_info['quantity'] * stock_info['avg_price'],
                'profit_loss': stock_info['profit_loss'],
                'profit_rate': stock_info['profit_rate']
            })
        
        # 4. CSV 저장
        self.csv.update_portfolio(portfolio_data)
        
        print(f"✅ 포트폴리오 업데이트 완료 ({len(portfolio_data)}개 종목)")
        
        return True
    
    def check_rebalancing_needed(self) -> bool:
        """리밸런싱 필요 여부 확인"""
        
        rebalance_cfg = self.cfg.get('REBALANCING', {})
        
        if not rebalance_cfg.get('enabled', False):
            return False
        
        # 다음 리밸런싱 날짜 확인
        next_date_str = rebalance_cfg.get('next_date')
        if not next_date_str:
            return False
        
        next_date = datetime.strptime(next_date_str, '%Y-%m-%d')
        today = datetime.now()
        
        if today.date() >= next_date.date():
            print(f"📅 리밸런싱 시기입니다! (예정일: {next_date_str})")
            return True
        
        return False
    
    def get_portfolio_summary(self) -> Dict:
        """포트폴리오 요약 통계"""
        
        portfolio = self.csv.get_portfolio()
        
        if not portfolio:
            return None
        
        total_invest = sum(float(p['투자금액']) for p in portfolio)
        total_eval = sum(float(p['평가금액']) for p in portfolio)
        total_profit_loss = total_eval - total_invest
        total_profit_rate = (total_profit_loss / total_invest * 100) if total_invest > 0 else 0
        
        stocks = []
        for p in portfolio:
            stocks.append({
                'name': p['ETF명'],
                'quantity': int(p['보유수량']),
                'profit_loss': float(p['평가손익']),
                'profit_rate': float(p['수익률(%)'])
            })
        
        return {
            'total_invest': total_invest,
            'total_eval': total_eval,
            'total_profit_loss': total_profit_loss,
            'total_profit_rate': total_profit_rate,
            'stock_count': len(portfolio),
            'stocks': stocks
        }


# 테스트 코드
if __name__ == "__main__":
    strategy = TradingStrategy()
    
    print("\n" + "="*70)
    print("🧪 TradingStrategy 테스트")
    print("="*70)
    
    # 1. 계좌 상태 확인
    print("\n1️⃣  계좌 상태 확인")
    strategy.api.check_account_status()
    
    # 2. 정기 매수일 체크
    print("\n2️⃣  정기 매수일 체크")
    is_buy_day = strategy.check_monthly_buy_day()
    print(f"   오늘은 정기 매수일: {'✅ YES' if is_buy_day else '❌ NO'}")
    
    # 3. 하락 기회 체크
    print("\n3️⃣  하락 매수 기회 체크")
    opportunities = strategy.check_dip_opportunity()
    print(f"   하락 종목: {len(opportunities)}개")
    
    # 4. 포트폴리오 상태 업데이트
    print("\n4️⃣  포트폴리오 상태 업데이트")
    strategy.update_portfolio_status()
    
    # 5. 포트폴리오 요약
    print("\n5️⃣  포트폴리오 요약")
    summary = strategy.get_portfolio_summary()
    if summary:
        print(f"   총 투자금: {summary['total_invest']:,.0f}원")
        print(f"   총 평가금: {summary['total_eval']:,.0f}원")
        print(f"   수익률: {summary['total_profit_rate']:+.2f}%")
    
    print("\n✅ 테스트 완료!")