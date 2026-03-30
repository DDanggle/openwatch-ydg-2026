-- ============================================================
-- 의원 마스터
-- ============================================================
CREATE TABLE IF NOT EXISTS politician_master (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    party           TEXT,              -- 소속 (국회)
    position        TEXT,              -- 직위 (국회의원, 국회의장 등)
    constituency    TEXT,
    assembly_terms  TEXT,              -- JSON array
    latest_elected  INTEGER,
    birth_year      INTEGER,
    gender          TEXT,
    raw_json        TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_politician_name ON politician_master(name);
CREATE INDEX IF NOT EXISTS idx_politician_party ON politician_master(party);

-- ============================================================
-- 개별 자산 항목 (원본 데이터)
-- ============================================================
CREATE TABLE IF NOT EXISTS asset_itemized (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    politician_id     TEXT    NOT NULL REFERENCES politician_master(id),
    disclosure_date   TEXT    NOT NULL,       -- '202303' 등
    disclosure_year   INTEGER NOT NULL,
    asset_type        TEXT    NOT NULL,       -- 건물/부동산/예금/채무/증권/보석류
    relation          TEXT    NOT NULL,       -- 본인/배우자/부/모/장남/장녀
    kind              TEXT,
    detail            TEXT,
    origin_valuation  INTEGER DEFAULT 0,
    increased_amount  INTEGER DEFAULT 0,
    decreased_amount  INTEGER DEFAULT 0,
    current_valuation INTEGER DEFAULT 0,
    reason            TEXT,
    raw_json          TEXT,
    created_at        TEXT DEFAULT (datetime('now')),
    UNIQUE(politician_id, disclosure_date, asset_type, relation, kind, detail)
);

CREATE INDEX IF NOT EXISTS idx_asset_politician ON asset_itemized(politician_id);
CREATE INDEX IF NOT EXISTS idx_asset_year ON asset_itemized(disclosure_year);
CREATE INDEX IF NOT EXISTS idx_asset_type ON asset_itemized(asset_type);
CREATE INDEX IF NOT EXISTS idx_asset_politician_year ON asset_itemized(politician_id, disclosure_year);

-- ============================================================
-- 연도별 집계 (asset_itemized에서 파생)
-- ============================================================
CREATE TABLE IF NOT EXISTS asset_disclosure_yearly (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    politician_id     TEXT    NOT NULL REFERENCES politician_master(id),
    disclosure_year   INTEGER NOT NULL,
    total_assets      INTEGER DEFAULT 0,
    total_debt        INTEGER DEFAULT 0,
    net_assets        INTEGER DEFAULT 0,
    real_estate_total INTEGER DEFAULT 0,
    deposit_total     INTEGER DEFAULT 0,
    securities_total  INTEGER DEFAULT 0,
    self_total        INTEGER DEFAULT 0,
    spouse_total      INTEGER DEFAULT 0,
    family_total      INTEGER DEFAULT 0,
    yoy_change        INTEGER DEFAULT 0,
    yoy_change_pct    REAL    DEFAULT 0.0,
    computed_at       TEXT DEFAULT (datetime('now')),
    UNIQUE(politician_id, disclosure_year)
);

CREATE INDEX IF NOT EXISTS idx_yearly_politician ON asset_disclosure_yearly(politician_id);
CREATE INDEX IF NOT EXISTS idx_yearly_year ON asset_disclosure_yearly(disclosure_year);

-- ============================================================
-- 부동산 실거래 매칭
-- ============================================================
CREATE TABLE IF NOT EXISTS real_estate_match (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_item_id           INTEGER NOT NULL REFERENCES asset_itemized(id),
    politician_id           TEXT    NOT NULL REFERENCES politician_master(id),
    sido                    TEXT,
    sigungu                 TEXT,
    dong                    TEXT,
    apartment_name          TEXT,
    area_sqm                REAL,
    matched_trade_price     INTEGER,
    match_confidence        REAL    DEFAULT 0.0,
    match_method            TEXT,            -- 'exact', 'fuzzy_name', 'dong_area', 'sigungu_avg'
    declared_valuation      INTEGER DEFAULT 0,
    estimated_market_value  INTEGER DEFAULT 0,
    gap_amount              INTEGER DEFAULT 0,
    gap_pct                 REAL    DEFAULT 0.0,
    raw_trade_json          TEXT,
    created_at              TEXT DEFAULT (datetime('now')),
    UNIQUE(asset_item_id)
);

CREATE INDEX IF NOT EXISTS idx_match_politician ON real_estate_match(politician_id);
CREATE INDEX IF NOT EXISTS idx_match_gap ON real_estate_match(gap_pct);

-- ============================================================
-- 파생 지표 (분석 결과 캐싱)
-- ============================================================
CREATE TABLE IF NOT EXISTS derived_metrics (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    politician_id               TEXT    NOT NULL REFERENCES politician_master(id),
    analysis_start_year         INTEGER NOT NULL,
    analysis_end_year           INTEGER NOT NULL,
    cagr                        REAL,
    absolute_growth             INTEGER,
    growth_rate                 REAL,
    growth_rank                 INTEGER,
    family_contribution_ratio   REAL,
    spouse_contribution_ratio   REAL,
    family_growth_share         REAL,
    avg_gap_pct                 REAL,
    max_gap_pct                 REAL,
    matched_property_count      INTEGER,
    total_property_count        INTEGER,
    anomaly_flags               TEXT,           -- JSON
    anomaly_score               REAL DEFAULT 0.0,
    computed_at                 TEXT DEFAULT (datetime('now')),
    UNIQUE(politician_id, analysis_start_year, analysis_end_year)
);

CREATE INDEX IF NOT EXISTS idx_metrics_politician ON derived_metrics(politician_id);
CREATE INDEX IF NOT EXISTS idx_metrics_cagr ON derived_metrics(cagr);
CREATE INDEX IF NOT EXISTS idx_metrics_anomaly ON derived_metrics(anomaly_score);

-- ============================================================
-- 실거래가 API 응답 캐시
-- ============================================================
CREATE TABLE IF NOT EXISTS trade_data_cache (
    lawd_cd       TEXT NOT NULL,
    deal_ymd      TEXT NOT NULL,
    response_json TEXT,
    fetched_at    TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (lawd_cd, deal_ymd)
);
