import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import io

# 한글 폰트 설정 (Mac)
import platform
import os
from matplotlib import font_manager, rc

# 경고 메시지 숨기기
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

def get_korean_font_prop():
    """한글 폰트 속성 반환"""
    if platform.system() == 'Darwin':  # Mac
        # NanumGothic 폰트 직접 로드
        nanum_paths = [
            '/Users/joon/Library/Fonts/NanumGothic-Regular.ttf',
            '/Library/Fonts/NanumGothic-Regular.ttf',
            os.path.expanduser('~/Library/Fonts/NanumGothic-Regular.ttf')
        ]

        for font_path in nanum_paths:
            if os.path.exists(font_path):
                print(f"✅ 한글 폰트 로드: {font_path}")
                return font_manager.FontProperties(fname=font_path)

        # 대체: AppleGothic
        apple_path = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'
        if os.path.exists(apple_path):
            print(f"✅ 한글 폰트 로드: AppleGothic")
            return font_manager.FontProperties(fname=apple_path)

    print("⚠️  한글 폰트를 찾을 수 없습니다.")
    return None

# 한글 폰트 속성 가져오기
korean_font = get_korean_font_prop()
plt.rcParams['axes.unicode_minus'] = False

class ChartGenerator:
    """투자 차트 생성기"""

    def __init__(self, output_dir='charts'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # 차트 스타일
        plt.style.use('seaborn-v0_8-darkgrid')

        # 색상 팔레트
        self.colors = {
            'primary': '#3498db',
            'success': '#2ecc71',
            'danger': '#e74c3c',
            'warning': '#f39c12',
            'info': '#9b59b6'
        }
    
    def create_portfolio_pie_chart(self, portfolio_data):
        """포트폴리오 구성 원형 차트
        
        Args:
            portfolio_data: [{'name': 'ETF명', 'value': 평가금액}, ...]
        
        Returns:
            str: 이미지 파일 경로
        """
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        names = [item['name'] for item in portfolio_data]
        values = [item['value'] for item in portfolio_data]
        
        # 색상 생성
        colors = plt.cm.Set3(np.linspace(0, 1, len(names)))
        
        # 원형 차트
        wedges, texts, autotexts = ax.pie(
            values,
            labels=names,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            textprops={'fontsize': 10, 'weight': 'bold'}
        )

        # 한글 폰트 적용
        for text in texts:
            if korean_font:
                text.set_fontproperties(korean_font)

        # 퍼센트 텍스트 스타일
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(11)

        ax.set_title('포트폴리오 구성', fontsize=16, weight='bold', pad=20, fontproperties=korean_font if korean_font else None)
        
        # 범례 추가
        total = sum(values)
        legend_labels = [
            f"{name}: {value:,.0f}원 ({value/total*100:.1f}%)"
            for name, value in zip(names, values)
        ]
        legend = ax.legend(legend_labels, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1), prop=korean_font if korean_font else None)
        
        plt.tight_layout()
        
        # 저장
        filename = f"portfolio_pie_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def create_return_bar_chart(self, etf_returns):
        """ETF별 수익률 막대 차트
        
        Args:
            etf_returns: [{'name': 'ETF명', 'return': 수익률}, ...]
        
        Returns:
            str: 이미지 파일 경로
        """
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 데이터 정렬 (수익률 높은 순)
        sorted_data = sorted(etf_returns, key=lambda x: x['return'], reverse=True)
        
        names = [item['name'] for item in sorted_data]
        returns = [item['return'] for item in sorted_data]
        
        # 색상 (양수/음수)
        colors = [self.colors['success'] if r >= 0 else self.colors['danger'] for r in returns]
        
        # 막대 차트
        bars = ax.barh(names, returns, color=colors, edgecolor='black', linewidth=0.5)
        
        # 값 레이블 추가
        for i, (bar, value) in enumerate(zip(bars, returns)):
            x_pos = value + (0.5 if value >= 0 else -0.5)
            ax.text(x_pos, i, f'{value:+.2f}%', 
                   va='center', ha='left' if value >= 0 else 'right',
                   fontsize=10, weight='bold')
        
        ax.axvline(x=0, color='black', linewidth=0.8, linestyle='-')
        ax.set_xlabel('수익률 (%)', fontsize=12, weight='bold', fontproperties=korean_font if korean_font else None)
        ax.set_title('ETF별 수익률', fontsize=16, weight='bold', pad=20, fontproperties=korean_font if korean_font else None)
        ax.grid(axis='x', alpha=0.3)

        # Y축 레이블에 한글 폰트 적용
        if korean_font:
            for label in ax.get_yticklabels():
                label.set_fontproperties(korean_font)
        
        plt.tight_layout()
        
        # 저장
        filename = f"return_bar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def create_cumulative_return_chart(self, date_data):
        """누적 수익률 추이 차트
        
        Args:
            date_data: [{'date': 'YYYY-MM-DD', 'total_value': 총평가액, 'invested': 투자금}, ...]
        
        Returns:
            str: 이미지 파일 경로
        """
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                       gridspec_kw={'height_ratios': [2, 1]})
        
        df = pd.DataFrame(date_data)
        df['date'] = pd.to_datetime(df['date'])
        df['return'] = (df['total_value'] - df['invested']) / df['invested'] * 100
        
        # 상단: 총자산 vs 투자금
        ax1.plot(df['date'], df['total_value'], 
                label='총 평가액', color=self.colors['primary'], 
                linewidth=2.5, marker='o', markersize=4)
        ax1.plot(df['date'], df['invested'], 
                label='총 투자금', color=self.colors['warning'], 
                linewidth=2.5, linestyle='--', marker='s', markersize=4)
        
        ax1.fill_between(df['date'], df['invested'], df['total_value'], 
                         where=(df['total_value'] >= df['invested']),
                         color=self.colors['success'], alpha=0.2, label='수익')
        ax1.fill_between(df['date'], df['invested'], df['total_value'], 
                         where=(df['total_value'] < df['invested']),
                         color=self.colors['danger'], alpha=0.2, label='손실')
        
        ax1.set_ylabel('금액 (원)', fontsize=12, weight='bold')
        ax1.set_title('💰 총자산 추이', fontsize=16, weight='bold', pad=20)
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        # 하단: 수익률
        colors_return = [self.colors['success'] if r >= 0 else self.colors['danger'] 
                        for r in df['return']]
        ax2.bar(df['date'], df['return'], color=colors_return, 
               edgecolor='black', linewidth=0.5, alpha=0.8)
        
        ax2.axhline(y=0, color='black', linewidth=0.8, linestyle='-')
        ax2.axhline(y=12, color='green', linewidth=1, linestyle='--', alpha=0.5, label='목표 12%')
        ax2.axhline(y=17, color='green', linewidth=1, linestyle='--', alpha=0.5, label='목표 17%')
        
        ax2.set_xlabel('날짜', fontsize=12, weight='bold')
        ax2.set_ylabel('수익률 (%)', fontsize=12, weight='bold')
        ax2.set_title('📊 누적 수익률', fontsize=14, weight='bold', pad=15)
        ax2.legend(loc='upper left', fontsize=9)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 저장
        filename = f"cumulative_return_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def create_monthly_investment_chart(self, monthly_data):
        """월별 투자금액 차트
        
        Args:
            monthly_data: [{'month': 'YYYY-MM', 'regular': 정기, 'dip': 기회}, ...]
        
        Returns:
            str: 이미지 파일 경로
        """
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        df = pd.DataFrame(monthly_data)
        months = df['month']
        regular = df['regular']
        dip = df['dip']
        
        x = np.arange(len(months))
        width = 0.35
        
        # 누적 막대 차트
        bars1 = ax.bar(x, regular, width, label='정기 매수', 
                      color=self.colors['primary'], edgecolor='black', linewidth=0.5)
        bars2 = ax.bar(x, dip, width, bottom=regular, label='기회 매수', 
                      color=self.colors['success'], edgecolor='black', linewidth=0.5)
        
        # 합계 라인
        total = regular + dip
        ax.plot(x, total, color='red', marker='o', linewidth=2, 
               markersize=8, label='월 합계', linestyle='--')
        
        # 값 레이블
        for i, (r, d, t) in enumerate(zip(regular, dip, total)):
            if r > 0:
                ax.text(i, r/2, f'{r/10000:.0f}만', 
                       ha='center', va='center', fontsize=9, weight='bold', color='white')
            if d > 0:
                ax.text(i, r + d/2, f'{d/10000:.0f}만', 
                       ha='center', va='center', fontsize=9, weight='bold', color='white')
            ax.text(i, t + max(total)*0.03, f'{t/10000:.0f}만', 
                   ha='center', va='bottom', fontsize=10, weight='bold')
        
        ax.set_xlabel('월', fontsize=12, weight='bold')
        ax.set_ylabel('투자금액 (원)', fontsize=12, weight='bold')
        ax.set_title('📅 월별 투자 내역', fontsize=16, weight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha='right')
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(axis='y', alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        plt.tight_layout()
        
        # 저장
        filename = f"monthly_investment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def create_category_breakdown_chart(self, category_data):
        """카테고리별 분포 도넛 차트
        
        Args:
            category_data: [{'category': '카테고리', 'value': 금액}, ...]
        
        Returns:
            str: 이미지 파일 경로
        """
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        categories = [item['category'] for item in category_data]
        values = [item['value'] for item in category_data]
        
        # 색상
        colors = [self.colors['primary'], self.colors['success'], 
                 self.colors['warning'], self.colors['info'], self.colors['danger']]
        colors = colors[:len(categories)]
        
        # 도넛 차트
        wedges, texts, autotexts = ax.pie(
            values,
            labels=categories,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            pctdistance=0.85,
            textprops={'fontsize': 11, 'weight': 'bold'}
        )
        
        # 가운데 원 (도넛 모양)
        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        ax.add_artist(centre_circle)
        
        # 중앙 텍스트
        total = sum(values)
        ax.text(0, 0, f'{total:,.0f}원', 
               ha='center', va='center', fontsize=18, weight='bold')
        
        # 퍼센트 텍스트 스타일
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(12)
            autotext.set_weight('bold')
        
        ax.set_title('카테고리별 자산 분포', fontsize=16, weight='bold', pad=20, fontproperties=korean_font if korean_font else None)

        # 레이블에 한글 폰트 적용
        if korean_font:
            for text in ax.texts:
                text.set_fontproperties(korean_font)
        
        plt.tight_layout()
        
        # 저장
        filename = f"category_breakdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def create_dashboard(self, dashboard_data):
        """종합 대시보드 (4개 차트)
        
        Args:
            dashboard_data: {
                'portfolio': [...],
                'returns': [...],
                'monthly': [...],
                'categories': [...]
            }
        
        Returns:
            str: 이미지 파일 경로
        """
        
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        # 1. 포트폴리오 구성 (좌상)
        ax1 = fig.add_subplot(gs[0, 0])
        portfolio_data = dashboard_data.get('portfolio', [])
        if portfolio_data:
            names = [item['name'] for item in portfolio_data]
            values = [item['value'] for item in portfolio_data]
            colors = plt.cm.Set3(np.linspace(0, 1, len(names)))
            
            ax1.pie(values, labels=names, autopct='%1.1f%%', 
                   startangle=90, colors=colors)
            ax1.set_title('📊 포트폴리오 구성', fontsize=14, weight='bold', pad=10)
        
        # 2. ETF별 수익률 (우상)
        ax2 = fig.add_subplot(gs[0, 1])
        returns_data = dashboard_data.get('returns', [])
        if returns_data:
            sorted_returns = sorted(returns_data, key=lambda x: x['return'], reverse=True)
            names = [item['name'] for item in sorted_returns]
            returns = [item['return'] for item in sorted_returns]
            colors = [self.colors['success'] if r >= 0 else self.colors['danger'] 
                     for r in returns]
            
            bars = ax2.barh(names, returns, color=colors)
            ax2.axvline(x=0, color='black', linewidth=0.8)
            ax2.set_xlabel('수익률 (%)')
            ax2.set_title('📈 ETF별 수익률', fontsize=14, weight='bold', pad=10)
            ax2.grid(axis='x', alpha=0.3)
        
        # 3. 월별 투자 (좌하)
        ax3 = fig.add_subplot(gs[1, 0])
        monthly_data = dashboard_data.get('monthly', [])
        if monthly_data:
            df = pd.DataFrame(monthly_data)
            months = df['month']
            regular = df['regular']
            dip = df['dip']
            x = np.arange(len(months))
            width = 0.7
            
            ax3.bar(x, regular, width, label='정기', color=self.colors['primary'])
            ax3.bar(x, dip, width, bottom=regular, label='기회', color=self.colors['success'])
            ax3.set_xlabel('월')
            ax3.set_ylabel('투자금액 (원)')
            ax3.set_title('📅 월별 투자 내역', fontsize=14, weight='bold', pad=10)
            ax3.set_xticks(x)
            ax3.set_xticklabels(months, rotation=45, ha='right')
            ax3.legend()
            ax3.grid(axis='y', alpha=0.3)
        
        # 4. 카테고리별 분포 (우하)
        ax4 = fig.add_subplot(gs[1, 1])
        category_data = dashboard_data.get('categories', [])
        if category_data:
            categories = [item['category'] for item in category_data]
            values = [item['value'] for item in category_data]
            colors_cat = plt.cm.Set2(np.linspace(0, 1, len(categories)))
            
            wedges, texts, autotexts = ax4.pie(
                values, labels=categories, autopct='%1.1f%%',
                startangle=90, colors=colors_cat, pctdistance=0.85
            )
            centre_circle = plt.Circle((0, 0), 0.70, fc='white')
            ax4.add_artist(centre_circle)
            ax4.set_title('📂 카테고리별 분포', fontsize=14, weight='bold', pad=10)
        
        fig.suptitle('📊 투자 종합 대시보드', fontsize=20, weight='bold', y=0.98)
        
        # 저장
        filename = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filepath)


# 테스트 코드
if __name__ == "__main__":
    chart_gen = ChartGenerator()
    
    # 1. 포트폴리오 원형 차트
    portfolio = [
        {'name': 'TIGER 미국나스닥100', 'value': 477840},
        {'name': 'ACE 미국빅테크TOP7', 'value': 195975},
        {'name': 'TIGER 미국S&P500', 'value': 286800}
    ]
    file1 = chart_gen.create_portfolio_pie_chart(portfolio)
    print(f"✅ 포트폴리오 차트: {file1}")
    
    # 2. 수익률 막대 차트
    returns = [
        {'name': 'TIGER 미국나스닥100', 'return': 5.2},
        {'name': 'ACE 미국빅테크TOP7', 'return': 7.8},
        {'name': 'TIGER 미국S&P500', 'return': 3.1}
    ]
    file2 = chart_gen.create_return_bar_chart(returns)
    print(f"✅ 수익률 차트: {file2}")
    
    print("\n✅ 차트 생성 테스트 완료!")