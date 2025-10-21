import requests
import json
import yaml
import time

class KISApi:
    """한국투자증권 OpenAPI - ISA 계좌 지원"""
    
    def __init__(self, config_path='config.yaml'):
        with open(config_path, encoding='UTF-8') as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
        
        self.app_key = cfg['APP_KEY']
        self.app_secret = cfg['APP_SECRET']
        self.cano = cfg['CANO']
        self.acnt_prdt_cd = cfg['ACNT_PRDT_CD']
        self.url_base = cfg['URL_BASE']
        self.account_type = cfg.get('ACCOUNT_TYPE', 'NORMAL')
        self.isa_constraints = cfg.get('ISA_CONSTRAINTS', {})
        
        self.access_token = self.get_access_token()
        
        # ISA 계좌 체크
        if self.account_type == 'ISA':
            print("✅ ISA 계좌 모드로 실행됩니다.")
            self._check_isa_constraints()
    
    def _check_isa_constraints(self):
        """ISA 계좌 제약사항 확인"""
        print("\n⚠️  ISA 계좌 제약사항:")
        if self.isa_constraints.get('only_domestic'):
            print("  - 국내 상장 ETF만 거래 가능")
        if self.isa_constraints.get('no_credit'):
            print("  - 신용거래 불가")
        if self.isa_constraints.get('no_derivative'):
            print("  - 파생상품 거래 불가")
        if self.isa_constraints.get('no_reserve'):
            print("  - 예약주문 불가")
        print()
    
    def get_access_token(self):
        """토큰 발급"""
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        url = f"{self.url_base}/oauth2/tokenP"
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            token = res.json()["access_token"]
            print(f"✅ Access Token 발급 성공")
            return token
        except Exception as e:
            print(f"❌ Token 발급 실패: {e}")
            return None
    
    def _hashkey(self, datas):
        """해시키 생성"""
        path = "uapi/hashkey"
        url = f"{self.url_base}/{path}"
        
        headers = {
            'content-Type': 'application/json',
            'appKey': self.app_key,
            'appSecret': self.app_secret
        }
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(datas))
            return res.json()["HASH"]
        except Exception as e:
            print(f"❌ Hashkey 생성 실패: {e}")
            return ""
    
    def get_domestic_etf_price(self, code):
        """국내 ETF 현재가 조회 (ISA 계좌용)"""
        path = "uapi/domestic-stock/v1/quotations/inquire-price"
        url = f"{self.url_base}/{path}"
        
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010100"
        }
        
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()

            output = res.json()['output']

            # 디버그: 실제 응답 필드 확인
            # print(f"DEBUG - Available fields: {output.keys()}")

            return {
                'code': code,
                'current_price': int(output['stck_prpr']),
                'high_52w': int(output.get('stck_sdpr', 0)),
                'low_52w': int(output.get('stck_lwpr', 0)),
                'prev_close': int(output.get('stck_prdy_clpr', output.get('stck_prpr', 0))),
                'change': int(output.get('prdy_vrss', 0)),
                'change_rate': float(output.get('prdy_ctrt', 0)),
                'volume': int(output.get('acml_vol', 0))
            }
        except Exception as e:
            print(f"❌ 가격 조회 실패 ({code}): {e}")
            return None
    
    def get_balance(self):
        """현금 잔고 조회"""
        path = "uapi/domestic-stock/v1/trading/inquire-psbl-order"
        url = f"{self.url_base}/{path}"
        
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTC8908R",
            "custtype": "P"
        }
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": "005930",
            "ORD_UNPR": "0",
            "ORD_DVSN": "01",
            "CMA_EVLU_AMT_ICLD_YN": "Y",
            "OVRS_ICLD_YN": "Y"
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            cash = int(res.json()['output']['ord_psbl_cash'])
            return cash
        except Exception as e:
            print(f"❌ 잔고 조회 실패: {e}")
            return 0
    
    def get_stock_balance(self):
        """주식 잔고 조회 (ISA 계좌 포함)"""
        path = "uapi/domestic-stock/v1/trading/inquire-balance"
        url = f"{self.url_base}/{path}"
        
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTC8434R",
            "custtype": "P"
        }
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            
            data = res.json()
            stocks = {}

            for stock in data['output1']:
                qty = int(stock.get('hldg_qty', 0))
                if qty > 0:
                    stocks[stock['pdno']] = {
                        'name': stock.get('prdt_name', ''),
                        'quantity': qty,
                        'avg_price': float(stock.get('pchs_avg_pric', 0)),
                        'current_price': int(stock.get('prpr', 0)),
                        'eval_amt': int(stock.get('evlu_amt', 0)),
                        'profit_loss': int(stock.get('evlu_pfls_amt', 0)),
                        'profit_rate': float(stock.get('evlu_pfls_rt', 0))
                    }

            evaluation = data['output2'][0] if data.get('output2') else {}
            summary = {
                'stocks': stocks,
                'total_eval_amt': int(evaluation.get('tot_evlu_amt', 0)),
                'stock_eval_amt': int(evaluation.get('scts_evlu_amt', 0)),
                'profit_loss': int(evaluation.get('evlu_pfls_smtl_amt', 0)),
                'profit_rate': float(evaluation.get('evlu_pfls_rt', 0))
            }
            
            return summary
            
        except Exception as e:
            print(f"❌ 주식잔고 조회 실패: {e}")
            return None
    
    def buy_order(self, code, quantity, order_type="01"):
        """매수 주문 (ISA 계좌 지원)
        
        Args:
            code: 종목코드
            quantity: 수량
            order_type: 주문구분
                - "01": 시장가
                - "00": 지정가 (ISA에서 권장)
        """
        # ISA 제약사항 체크
        if self.account_type == 'ISA':
            if self.isa_constraints.get('only_domestic'):
                if not code.isdigit() or len(code) != 6:
                    print(f"❌ ISA 계좌는 국내 주식만 거래 가능합니다: {code}")
                    return None
        
        path = "uapi/domestic-stock/v1/trading/order-cash"
        url = f"{self.url_base}/{path}"
        
        data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0"  # 시장가의 경우 0
        }
        
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTC0802U",  # 실전투자 매수
            "custtype": "P",
            "hashkey": self._hashkey(data)
        }
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(data))
            result = res.json()
            
            if result['rt_cd'] == '0':
                print(f"✅ 매수 주문 성공: {code} {quantity}주")
                return {
                    'success': True,
                    'order_no': result['output']['ORD_NO'],
                    'code': code,
                    'quantity': quantity,
                    'msg': result['msg1']
                }
            else:
                print(f"❌ 매수 주문 실패: {result['msg1']}")
                return {
                    'success': False,
                    'msg': result['msg1']
                }
                
        except Exception as e:
            print(f"❌ 매수 주문 에러: {e}")
            return None
    
    def sell_order(self, code, quantity, order_type="01"):
        """매도 주문 (ISA 계좌 지원)"""
        path = "uapi/domestic-stock/v1/trading/order-cash"
        url = f"{self.url_base}/{path}"
        
        data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0"
        }
        
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTC0801U",  # 실전투자 매도
            "custtype": "P",
            "hashkey": self._hashkey(data)
        }
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(data))
            result = res.json()
            
            if result['rt_cd'] == '0':
                print(f"✅ 매도 주문 성공: {code} {quantity}주")
                return {
                    'success': True,
                    'order_no': result['output']['ORD_NO'],
                    'code': code,
                    'quantity': quantity,
                    'msg': result['msg1']
                }
            else:
                print(f"❌ 매도 주문 실패: {result['msg1']}")
                return {
                    'success': False,
                    'msg': result['msg1']
                }
                
        except Exception as e:
            print(f"❌ 매도 주문 에러: {e}")
            return None
    
    def check_account_status(self):
        """계좌 상태 확인 (ISA 계좌 등록 여부)"""
        try:
            balance = self.get_balance()
            stocks = self.get_stock_balance()
            
            print("\n" + "="*50)
            print(f"📊 계좌 상태 확인 ({self.account_type})")
            print("="*50)
            print(f"계좌번호: {self.cano}-{self.acnt_prdt_cd}")
            print(f"주문가능현금: {balance:,}원")
            
            if stocks:
                print(f"총 평가금액: {stocks['total_eval_amt']:,}원")
                print(f"평가손익: {stocks['profit_loss']:,}원 ({stocks['profit_rate']:.2f}%)")
                print(f"보유종목수: {len(stocks['stocks'])}개")
            
            print("="*50 + "\n")
            
            return True
            
        except Exception as e:
            print(f"❌ 계좌 상태 확인 실패: {e}")
            print("⚠️  ISA 계좌가 API에 등록되어 있는지 확인해주세요.")
            return False

# 테스트 코드
if __name__ == "__main__":
    api = KISApi()
    
    # 계좌 상태 확인
    if api.check_account_status():
        print("✅ API 연동 성공")
        
        # 가격 조회 테스트
        price = api.get_domestic_etf_price("133690")
        if price:
            print(f"\n📊 TIGER 나스닥100 현재가: {price['current_price']:,}원")
    else:
        print("❌ API 연동 실패")