# ETF 자동투자 시스템

한국투자증권 API를 활용한 ETF 자동투자 시스템입니다.

## 주요 기능

- 📅 **월별 정기 매수**: 매달 지정일에 자동으로 ETF 매수
- 📉 **하락 매수**: 52주 최고가 대비 -5% 이상 하락 시 기회 매수
- 💼 **ISA 계좌 지원**: ISA 계좌 제약사항 자동 검증
- 📊 **포트폴리오 배분**: EQUAL/WEIGHTED/CUSTOM 3가지 배분 방식
- 🔔 **Discord 알림**: 실시간 거래 알림 및 리포트
- 📝 **자동 기록**: CSV 기반 거래/포트폴리오 데이터 관리

## 설치

### 1. 환경 설정

```bash
# Conda 환경 생성 (권장)
conda create -n auto-trade python=3.13
conda activate auto-trade

# 또는 venv 사용
python3 -m venv venv
source venv/bin/activate
```

### 2. 패키지 설치

```bash
pip install schedule pyyaml requests
```

### 3. 설정 파일 생성

```bash
# 템플릿 복사
cp config.yaml.example config.yaml

# config.yaml 편집
# - APP_KEY, APP_SECRET: 한국투자증권 OpenAPI 키
# - CANO: ISA 계좌번호 (앞 8자리)
# - DISCORD_WEBHOOK_URL: Discord Webhook URL
```

## 사용 방법

### 정상 실행 (스케줄러 시작)

```bash
python main.py
```

자동으로 다음 작업이 스케줄링됩니다:
- 아침 리포트: 매일 09:00
- 정기 매수 체크: 매일 09:05
- 하락 매수 체크: 30분마다 (장 중)
- 주간 리포트: 월요일 09:00
- 월간 리포트: 매월 1일 09:00
- 포트폴리오 업데이트: 매일 15:35

### 테스트 모드

```bash
python main.py test
```

개별 기능을 수동으로 테스트할 수 있습니다.

### 상태 확인

```bash
python main.py status
```

계좌 상태 및 포트폴리오 현황을 확인합니다.

## 설정

### 투자 전략 설정

`config.yaml`에서 설정:

```yaml
STRATEGY:
  monthly_regular_amount: 500000  # 월 정기 매수 금액
  dip_buy_amount: 250000         # 하락 매수 금액
  dip_threshold: -5.0            # 하락 기준 (%)
  buy_day: 1                     # 매수일 (1~28)
  allocation_method: "WEIGHTED"  # 배분 방식
```

### ETF 추가/수정

```yaml
ETF_LIST:
  - code: "133690"
    name: "TIGER 미국나스닥100"
    category: "US_TECH"
    weight: 3                    # WEIGHTED 모드 가중치
    custom_ratio: 0.40           # CUSTOM 모드 비율
    priority: 1                  # 우선순위 (낮을수록 우선)
    enabled: true                # 활성화 여부
```

### 자동매매 모드

```yaml
ADVANCED:
  auto_trade: false  # false: 알림만, true: 자동 매매
```

⚠️ **주의**: 처음에는 반드시 `false`로 설정하고 알림만 받아보세요!

## 프로젝트 구조

```
.
├── main.py                    # 메인 실행 파일
├── config.yaml                # 설정 파일 (git 제외)
├── modules/
│   ├── kis_api.py            # 한투 API 래퍼
│   ├── strategy.py           # 매매 전략
│   ├── portfolio_allocator.py # 포트폴리오 배분
│   ├── csv_manager.py        # 데이터 관리
│   └── discord_bot.py        # Discord 알림
├── data/                      # CSV 데이터 (자동 생성)
└── reports/                   # 리포트 (자동 생성)
```

## Conda 환경에서 실행

```bash
# Conda 환경 활성화
conda activate auto-trade

# 실행
python main.py
```

## 주의사항

1. **API 키 관리**: `config.yaml`은 절대 공유하지 마세요
2. **ISA 계좌**: ISA 계좌는 국내 ETF만 거래 가능합니다
3. **테스트 먼저**: 실제 매매 전에 `auto_trade: false`로 충분히 테스트하세요
4. **장 시간**: 한국 주식시장 시간(09:00~15:30)에만 작동합니다

## 문제 해결

### Import 에러

```bash
# modules 폴더에 __init__.py 확인
ls modules/__init__.py

# 없으면 생성
touch modules/__init__.py
```

### API 에러

- API 키 만료 확인
- 한투 OpenAPI 홈페이지에서 키 재발급
- 장 시간인지 확인

## 라이선스

개인 투자용으로만 사용하세요. 투자 손실에 대한 책임은 본인에게 있습니다.

## 문의

문제가 있으면 Issue를 등록해주세요.
