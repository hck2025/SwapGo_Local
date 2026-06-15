"""초보자 학습용 용어사전 시드."""

from sqlalchemy.orm import Session

from app.services import glossary_service

GLOSSARY_SEED = [
    {
        "key": "slippage",
        "term_ko": "슬리피지",
        "term_en": "Slippage",
        "short_desc": "주문 시 예상 가격과 실제 체결 가격의 차이예요.",
        "long_desc": (
            "AMM에서는 거래 수량이 풀에 비해 클수록 가격이 더 많이 움직이고, 그만큼 슬리피지가 커져요. "
            "허용 슬리피지를 넘는 거래는 자동으로 취소됩니다."
        ),
        "example": "예상가 100 USDT인데 99.5 USDT에 체결되면 슬리피지 0.5%예요.",
        "related_keys": ["price_impact", "amm", "cpmm"],
        "difficulty": 1,
    },
    {
        "key": "price_impact",
        "term_ko": "가격 영향",
        "term_en": "Price Impact",
        "short_desc": "내 거래 한 번이 풀의 가격을 얼마나 움직이는지를 의미해요.",
        "long_desc": "큰 거래는 풀 비율을 크게 바꿔 다음 사람에게 불리한 가격을 만들 수 있어요.",
        "related_keys": ["slippage", "liquidity_pool"],
        "difficulty": 1,
    },
    {
        "key": "amm",
        "term_ko": "자동 마켓메이커",
        "term_en": "AMM",
        "short_desc": "오더북 없이 풀의 잔고로 즉시 가격을 결정해 거래하는 방식이에요.",
        "long_desc": "거래 상대방을 매번 찾을 필요가 없고, 풀에 모인 두 자산의 비율로 가격이 자동 결정돼요.",
        "related_keys": ["cpmm", "liquidity_pool"],
        "difficulty": 1,
    },
    {
        "key": "cpmm",
        "term_ko": "상수 곱 시장",
        "term_en": "Constant Product Market Maker",
        "short_desc": "x*y=k 공식을 유지하는 가장 보편적인 AMM 모델이에요.",
        "long_desc": "Uniswap V2가 채택한 모델로, 풀에 들어있는 두 자산 수량의 곱(k)을 일정하게 유지해요.",
        "example": "USDT 1,000,000과 ETH 500이 들어있으면 k=500,000,000이에요.",
        "related_keys": ["amm", "k_value"],
        "difficulty": 2,
    },
    {
        "key": "k_value",
        "term_ko": "k 값",
        "term_en": "Invariant k",
        "short_desc": "CPMM에서 두 자산 수량의 곱으로, 거래 전후 일정하게 유지돼요.",
        "long_desc": "유동성이 늘어나면 k도 커져 같은 거래의 가격 영향이 작아져요.",
        "related_keys": ["cpmm", "liquidity_pool"],
        "difficulty": 2,
    },
    {
        "key": "liquidity_pool",
        "term_ko": "유동성 풀",
        "term_en": "Liquidity Pool",
        "short_desc": "거래에 사용되는 두 자산이 함께 모여 있는 통이에요.",
        "long_desc": "유동성 공급자(LP)는 두 자산을 같은 가치 비율로 예치하고 LP 지분을 받아요. 거래 수수료는 LP에게 분배돼요.",
        "related_keys": ["amm", "lp_share", "impermanent_loss"],
        "difficulty": 1,
    },
    {
        "key": "lp_share",
        "term_ko": "LP 지분",
        "term_en": "LP Share",
        "short_desc": "유동성 풀에서 내 비중을 나타내는 가상의 토큰이에요.",
        "long_desc": "출금 시 LP 지분에 비례해 두 자산을 회수하게 돼요.",
        "related_keys": ["liquidity_pool", "impermanent_loss"],
        "difficulty": 2,
    },
    {
        "key": "impermanent_loss",
        "term_ko": "비영구적 손실",
        "term_en": "Impermanent Loss",
        "short_desc": "두 자산 가격이 갈라질수록 단순 보유 대비 손해가 생기는 현상이에요.",
        "long_desc": "거래 수수료 수익이 이 손실을 메우면 결과적으로 이득이 되기도 해요.",
        "related_keys": ["liquidity_pool", "lp_share"],
        "difficulty": 3,
    },
    {
        "key": "swap",
        "term_ko": "스왑",
        "term_en": "Swap",
        "short_desc": "두 자산을 풀의 비율에 맞춰 즉시 교환하는 거래예요.",
        "related_keys": ["amm", "slippage"],
        "difficulty": 1,
    },
    {
        "key": "gas",
        "term_ko": "가스",
        "term_en": "Gas",
        "short_desc": "블록체인에서 거래 처리에 드는 수수료예요.",
        "long_desc": "이 모의 환경에서는 별도 가스 비용 없이 0.3% 거래 수수료만 풀로 적립돼요.",
        "related_keys": ["swap"],
        "difficulty": 2,
    },
    {
        "key": "wallet",
        "term_ko": "지갑",
        "term_en": "Wallet",
        "short_desc": "공개키/개인키 한 쌍으로 자산을 관리하는 도구예요.",
        "long_desc": "이 거래소의 임시 지갑은 가입 시 1회만 개인키와 니모닉을 보여드려요. 잃어버리면 복구가 불가능합니다.",
        "related_keys": ["private_key", "mnemonic"],
        "difficulty": 1,
    },
    {
        "key": "private_key",
        "term_ko": "개인키",
        "term_en": "Private Key",
        "short_desc": "지갑의 자산을 사용할 수 있는 비밀 정보예요.",
        "long_desc": "다른 사람과 절대 공유하면 안 돼요. 서버에도 저장되지 않으니 분실 시 복구가 불가능합니다.",
        "related_keys": ["wallet", "mnemonic"],
        "difficulty": 2,
    },
    {
        "key": "mnemonic",
        "term_ko": "니모닉",
        "term_en": "Mnemonic Phrase",
        "short_desc": "12개 단어로 개인키를 백업하는 방식이에요.",
        "related_keys": ["wallet", "private_key"],
        "difficulty": 2,
    },
    {
        "key": "integrity",
        "term_ko": "거래 무결성",
        "term_en": "Ledger Integrity",
        "short_desc": "거래가 변조되지 않았음을 누구나 검증할 수 있는 성질이에요.",
        "long_desc": (
            "이 거래소는 모든 거래에 prev_hash와 본인 페이로드를 sha256으로 묶어 tx_hash를 만들어요. "
            "/explorer/verify에서 누구나 다시 계산해 무결성을 확인할 수 있어요."
        ),
        "related_keys": ["amm"],
        "difficulty": 2,
    },
]


def run(db: Session) -> None:
    glossary_service.upsert_terms(db, terms=GLOSSARY_SEED)
