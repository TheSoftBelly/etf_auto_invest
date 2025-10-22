#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
차트 생성 스크립트
현재 포트폴리오 데이터를 기반으로 다양한 차트를 생성합니다.
"""

import sys
from pathlib import Path

# modules 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from modules.csv_manager import CSVManager
from modules.chart_generator import ChartGenerator

def main():
    print("\n" + "="*70)
    print("📊 차트 생성 시작")
    print("="*70 + "\n")

    # CSV 매니저와 차트 생성기 초기화
    csv_mgr = CSVManager()
    chart_gen = ChartGenerator(output_dir='reports')

    # 포트폴리오 데이터 읽기
    portfolio = csv_mgr.get_portfolio()

    if not portfolio:
        print("❌ 포트폴리오 데이터가 없습니다.")
        return

    print(f"✅ 포트폴리오 데이터: {len(portfolio)}개 ETF\n")

    # 1. 포트폴리오 구성 원형 차트
    print("1️⃣  포트폴리오 구성 원형 차트 생성 중...")
    portfolio_chart_data = []
    for p in portfolio:
        portfolio_chart_data.append({
            'name': p['ETF명'],
            'value': float(p['평가금액'])
        })

    chart1 = chart_gen.create_portfolio_pie_chart(portfolio_chart_data)
    print(f"   ✅ 저장: {chart1}\n")

    # 2. ETF별 수익률 막대 차트
    print("2️⃣  ETF별 수익률 막대 차트 생성 중...")
    returns_chart_data = []
    for p in portfolio:
        returns_chart_data.append({
            'name': p['ETF명'],
            'return': float(p['수익률(%)'])
        })

    chart2 = chart_gen.create_return_bar_chart(returns_chart_data)
    print(f"   ✅ 저장: {chart2}\n")

    # 3. 카테고리별 분포 도넛 차트 (간단 버전)
    print("3️⃣  자산 분포 도넛 차트 생성 중...")

    # 실제로는 ETF 카테고리별로 묶어야 하지만,
    # 여기서는 간단히 각 ETF를 카테고리로 처리
    category_data = []
    for p in portfolio:
        category_data.append({
            'category': p['ETF명'][:15] + '...' if len(p['ETF명']) > 15 else p['ETF명'],
            'value': float(p['평가금액'])
        })

    chart3 = chart_gen.create_category_breakdown_chart(category_data)
    print(f"   ✅ 저장: {chart3}\n")

    # 통계 출력
    print("="*70)
    print("📈 포트폴리오 요약")
    print("="*70)

    stats = csv_mgr.calculate_portfolio_stats()
    print(f"총 투자금액: {stats['total_invest']:,.0f}원")
    print(f"총 평가금액: {stats['total_eval']:,.0f}원")
    print(f"평가손익: {stats['total_profit_loss']:+,.0f}원")
    print(f"수익률: {stats['total_profit_rate']:+.2f}%")
    print(f"보유 종목: {stats['stock_count']}개")

    print("\n" + "="*70)
    print("✅ 모든 차트 생성 완료!")
    print(f"📁 저장 위치: reports/")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
