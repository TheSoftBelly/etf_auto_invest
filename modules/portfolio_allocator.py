import yaml
from typing import List, Dict

class PortfolioAllocator:
    """포트폴리오 자동 배분 계산기"""
    
    def __init__(self, config_path='config.yaml'):
        with open(config_path, encoding='UTF-8') as f:
            self.cfg = yaml.load(f, Loader=yaml.FullLoader)
        
        self.strategy = self.cfg['STRATEGY']
        self.etf_list = self.cfg['ETF_LIST']
        self.allocation_method = self.strategy.get('allocation_method', 'EQUAL')
        self.category_limits = self.cfg.get('CATEGORY_LIMITS', {})
        
        # 활성화된 ETF만 필터링
        self.active_etfs = [etf for etf in self.etf_list if etf.get('enabled', True)]
        
        if not self.active_etfs:
            raise ValueError("활성화된 ETF가 없습니다!")
        
        print(f"✅ {len(self.active_etfs)}개 ETF 로드됨")
    
    def calculate_allocation(self, total_amount: float, mode='REGULAR') -> List[Dict]:
        """
        투자금액을 ETF별로 자동 배분
        
        Args:
            total_amount: 총 투자 금액
            mode: 'REGULAR' (정기매수) or 'DIP' (하락매수)
        
        Returns:
            [{
                'code': 'ETF코드',
                'name': 'ETF명',
                'allocated_amount': 배정금액,
                'ratio': 비율,
                'priority': 우선순위
            }, ...]
        """
        
        if mode == 'REGULAR':
            return self._calculate_regular_allocation(total_amount)
        elif mode == 'DIP':
            return self._calculate_dip_allocation(total_amount)
        else:
            raise ValueError(f"Unknown mode: {mode}")
    
    def _calculate_regular_allocation(self, total_amount: float) -> List[Dict]:
        """정기 매수 배분 계산"""
        
        if self.allocation_method == 'EQUAL':
            return self._equal_allocation(total_amount)
        
        elif self.allocation_method == 'WEIGHTED':
            return self._weighted_allocation(total_amount)
        
        elif self.allocation_method == 'CUSTOM':
            return self._custom_allocation(total_amount)
        
        else:
            raise ValueError(f"Unknown allocation method: {self.allocation_method}")
    
    def _equal_allocation(self, total_amount: float) -> List[Dict]:
        """균등 배분"""
        count = len(self.active_etfs)
        amount_per_etf = total_amount / count
        
        allocations = []
        for etf in self.active_etfs:
            allocations.append({
                'code': etf['code'],
                'name': etf['name'],
                'category': etf.get('category', 'UNKNOWN'),
                'allocated_amount': amount_per_etf,
                'ratio': 1.0 / count,
                'priority': etf.get('priority', 999)
            })
        
        return sorted(allocations, key=lambda x: x['priority'])
    
    def _weighted_allocation(self, total_amount: float) -> List[Dict]:
        """가중 배분"""
        
        # 총 가중치 합계
        total_weight = sum(etf.get('weight', 1) for etf in self.active_etfs)
        
        allocations = []
        for etf in self.active_etfs:
            weight = etf.get('weight', 1)
            ratio = weight / total_weight
            allocated_amount = total_amount * ratio
            
            allocations.append({
                'code': etf['code'],
                'name': etf['name'],
                'category': etf.get('category', 'UNKNOWN'),
                'allocated_amount': allocated_amount,
                'ratio': ratio,
                'priority': etf.get('priority', 999),
                'weight': weight
            })
        
        # 카테고리 제한 적용
        allocations = self._apply_category_limits(allocations, total_amount)
        
        return sorted(allocations, key=lambda x: x['priority'])
    
    def _custom_allocation(self, total_amount: float) -> List[Dict]:
        """사용자 정의 배분"""
        
        # 비율 합계 확인
        total_ratio = sum(etf.get('custom_ratio', 0) for etf in self.active_etfs)
        
        if abs(total_ratio - 1.0) > 0.01:
            print(f"⚠️  경고: custom_ratio 합계가 {total_ratio:.2%}입니다. (100%가 아님)")
            print("    자동으로 정규화합니다.")
        
        allocations = []
        for etf in self.active_etfs:
            ratio = etf.get('custom_ratio', 0) / total_ratio  # 정규화
            allocated_amount = total_amount * ratio
            
            allocations.append({
                'code': etf['code'],
                'name': etf['name'],
                'category': etf.get('category', 'UNKNOWN'),
                'allocated_amount': allocated_amount,
                'ratio': ratio,
                'priority': etf.get('priority', 999)
            })
        
        return sorted(allocations, key=lambda x: x['priority'])
    
    def _calculate_dip_allocation(self, total_amount: float) -> List[Dict]:
        """하락 매수 배분 계산"""
        
        dip_method = self.strategy.get('dip_allocation_method', 'FOCUS')
        
        if dip_method == 'FOCUS':
            # 하락한 종목에만 집중 투자 (외부에서 하락 종목만 필터링해서 넘겨야 함)
            return self._equal_allocation(total_amount)
        
        elif dip_method == 'EQUAL':
            return self._equal_allocation(total_amount)
        
        elif dip_method == 'WEIGHTED':
            return self._weighted_allocation(total_amount)
        
        else:
            return self._equal_allocation(total_amount)
    
    def _apply_category_limits(self, allocations: List[Dict], total_amount: float) -> List[Dict]:
        """카테고리별 한도 적용"""
        
        if not self.category_limits:
            return allocations
        
        # 카테고리별 배분액 계산
        category_totals = {}
        for alloc in allocations:
            cat = alloc['category']
            category_totals[cat] = category_totals.get(cat, 0) + alloc['allocated_amount']
        
        # 한도 초과 체크 및 조정
        adjusted = []
        for alloc in allocations:
            cat = alloc['category']
            limits = self.category_limits.get(cat, {})
            
            max_limit = limits.get('max_allocation')
            if max_limit:
                cat_total = category_totals[cat]
                cat_ratio = cat_total / total_amount
                
                if cat_ratio > max_limit:
                    # 초과분 비례 감소
                    scale_factor = max_limit / cat_ratio
                    alloc['allocated_amount'] *= scale_factor
                    alloc['ratio'] *= scale_factor
                    print(f"⚠️  {cat} 카테고리 한도 초과 → {max_limit:.0%}로 조정")
            
            adjusted.append(alloc)
        
        return adjusted
    
    def calculate_buy_quantities(self, allocations: List[Dict], current_prices: Dict[str, float]) -> List[Dict]:
        """
        배정 금액을 실제 매수 수량으로 변환
        
        Args:
            allocations: calculate_allocation() 결과
            current_prices: {'ETF코드': 현재가, ...}
        
        Returns:
            [{
                'code': 'ETF코드',
                'name': 'ETF명',
                'allocated_amount': 배정금액,
                'current_price': 현재가,
                'quantity': 매수수량,
                'actual_amount': 실제투자금액,
                'remainder': 잔액
            }, ...]
        """
        
        buy_orders = []
        total_remainder = 0
        
        for alloc in allocations:
            code = alloc['code']
            allocated = alloc['allocated_amount']
            
            if code not in current_prices:
                print(f"⚠️  {alloc['name']} ({code}) 가격 정보 없음 - 건너뜀")
                continue
            
            price = current_prices[code]
            quantity = int(allocated / price)  # 소수점 버림
            actual_amount = quantity * price
            remainder = allocated - actual_amount
            
            total_remainder += remainder
            
            buy_orders.append({
                'code': code,
                'name': alloc['name'],
                'category': alloc['category'],
                'allocated_amount': allocated,
                'current_price': price,
                'quantity': quantity,
                'actual_amount': actual_amount,
                'remainder': remainder,
                'priority': alloc['priority']
            })
        
        # 우선순위대로 정렬
        buy_orders = sorted(buy_orders, key=lambda x: x['priority'])
        
        # 잔액 재배분 (선택사항)
        if total_remainder > 0:
            buy_orders = self._redistribute_remainder(buy_orders, total_remainder)
        
        return buy_orders
    
    def _redistribute_remainder(self, buy_orders: List[Dict], total_remainder: float) -> List[Dict]:
        """잔액을 우선순위 높은 종목에 재배분"""
        
        print(f"\n💰 잔액 {total_remainder:,.0f}원 재배분 중...")
        
        for order in buy_orders:
            if total_remainder < order['current_price']:
                break
            
            # 추가 매수 가능한 수량
            additional_qty = int(total_remainder / order['current_price'])
            
            if additional_qty > 0:
                additional_amount = additional_qty * order['current_price']
                
                order['quantity'] += additional_qty
                order['actual_amount'] += additional_amount
                total_remainder -= additional_amount
                
                print(f"  ✅ {order['name']}: +{additional_qty}주 ({additional_amount:,.0f}원)")
        
        if total_remainder > 0:
            print(f"  💵 최종 잔액: {total_remainder:,.0f}원")
        
        return buy_orders
    
    def get_portfolio_summary(self, buy_orders: List[Dict]) -> Dict:
        """포트폴리오 요약 통계"""
        
        total_invested = sum(order['actual_amount'] for order in buy_orders)
        total_allocated = sum(order['allocated_amount'] for order in buy_orders)
        total_stocks = sum(order['quantity'] for order in buy_orders)
        
        category_breakdown = {}
        for order in buy_orders:
            cat = order['category']
            if cat not in category_breakdown:
                category_breakdown[cat] = {
                    'amount': 0,
                    'count': 0
                }
            category_breakdown[cat]['amount'] += order['actual_amount']
            category_breakdown[cat]['count'] += 1
        
        return {
            'total_allocated': total_allocated,
            'total_invested': total_invested,
            'efficiency': (total_invested / total_allocated * 100) if total_allocated > 0 else 0,
            'total_stocks': total_stocks,
            'etf_count': len(buy_orders),
            'category_breakdown': category_breakdown
        }
    
    def print_allocation_plan(self, buy_orders: List[Dict]):
        """배분 계획 출력"""
        
        summary = self.get_portfolio_summary(buy_orders)
        
        print("\n" + "="*70)
        print("📊 포트폴리오 배분 계획")
        print("="*70)
        
        print(f"\n💰 총 배정금액: {summary['total_allocated']:,.0f}원")
        print(f"💵 실제 투자금액: {summary['total_invested']:,.0f}원")
        print(f"📈 투자 효율: {summary['efficiency']:.1f}%")
        print(f"📦 총 매수 주식: {summary['total_stocks']}주 ({summary['etf_count']}개 ETF)")
        
        print(f"\n{'순위':<4} {'ETF명':<25} {'수량':<6} {'단가':<12} {'투자금액':<15}")
        print("-"*70)
        
        for i, order in enumerate(buy_orders, 1):
            if order['quantity'] > 0:
                print(
                    f"{i:<4} "
                    f"{order['name']:<25} "
                    f"{order['quantity']:<6} "
                    f"{order['current_price']:>10,}원 "
                    f"{order['actual_amount']:>13,}원"
                )
        
        # 카테고리별 요약
        if summary['category_breakdown']:
            print("\n📂 카테고리별 배분")
            print("-"*70)
            for cat, data in summary['category_breakdown'].items():
                ratio = (data['amount'] / summary['total_invested'] * 100) if summary['total_invested'] > 0 else 0
                print(f"  {cat:<20} {data['amount']:>12,}원 ({ratio:>5.1f}%) - {data['count']}개 ETF")
        
        print("="*70 + "\n")


# 테스트 코드
if __name__ == "__main__":
    allocator = PortfolioAllocator()
    
    print(f"\n✅ 배분 방식: {allocator.allocation_method}")
    print(f"✅ 활성화된 ETF: {len(allocator.active_etfs)}개\n")
    
    # 1. 정기 매수 배분 계획
    print("=" * 70)
    print("1️⃣  정기 매수 배분 (50만원)")
    print("=" * 70)
    
    allocations = allocator.calculate_allocation(500000, mode='REGULAR')
    
    for alloc in allocations:
        print(f"{alloc['name']:<30} {alloc['allocated_amount']:>10,.0f}원 ({alloc['ratio']:>5.1%})")
    
    # 2. 실제 매수 수량 계산
    print("\n" + "=" * 70)
    print("2️⃣  현재가 기준 매수 수량 계산")
    print("=" * 70)
    
    # 테스트용 현재가
    current_prices = {
        '133690': 159215,
        '465580': 21756,
        '360750': 23880,
        '390390': 23960
    }
    
    buy_orders = allocator.calculate_buy_quantities(allocations, current_prices)
    allocator.print_allocation_plan(buy_orders)
    
    # 3. 하락 매수 시뮬레이션
    print("=" * 70)
    print("3️⃣  하락 매수 배분 (25만원)")
    print("=" * 70)
    
    dip_allocations = allocator.calculate_allocation(250000, mode='DIP')
    dip_orders = allocator.calculate_buy_quantities(dip_allocations, current_prices)
    allocator.print_allocation_plan(dip_orders)