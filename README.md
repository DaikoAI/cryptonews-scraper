# Crypto News Scraper

Railway cronで実行される暗号通貨ニュースのスクレイピングアプリケーション

## 機能

- **自動スクレイピング**: CryptoPanicなどの暗号通貨ニュースサイトから記事を自動取得
- **PostgreSQL対応**: Drizzle ORMのdata_sourceテーブルに対応した永続化
- **効率的な差分更新**: 前回実行時以降の新記事のみを処理（CPU効率化）
- **重複回避**: URL基準での重複チェック機能
- **フォールバック**: PostgreSQL接続失敗時はJSONファイルに自動保存
- **Railway対応**: Railway環境での5分間隔自動実行に最適化

## アーキテクチャフロー

```mermaid
graph TD
    A[Railway Cron<br/>Every 5 minutes] --> B[Load Config<br/>Environment Variables]
    B --> C[Check Last Update<br/>PostgreSQL Query]
    C --> D[Start Selenium<br/>WebDriver]
    D --> E[CryptoPanic<br/>Scraper]
    E --> F[Extract Data<br/>Title, URL, Time, Currencies]
    F --> G[Filter New Articles<br/>Since Last Update]
    G --> H{New Articles?}
    H -->|No| I[Early Exit<br/>Save CPU]
    H -->|Yes| J[Create DataSource<br/>Objects]
    J --> K{PostgreSQL<br/>Available?}
    K -->|Yes| L[Save to DB<br/>data_source table]
    K -->|No| M[Fallback to JSON<br/>reports/ directory]
    L --> N[Update Success<br/>Log Results]
    M --> N
    I --> O[End]
    N --> O
```

## セットアップ

### 環境変数

`.env.example`をコピーして`.env`ファイルを作成し、環境に応じて設定してください：

```bash
# 設定ファイルをコピー
cp .env.example .env
```

主要な環境変数：

```bash
# PostgreSQL接続文字列（必須）
DATABASE_URL=postgresql://user:password@host:port/database

# Selenium設定（オプション - 環境により自動選択）
SELENIUM_BROWSER=chrome
SELENIUM_REMOTE_URL=http://localhost:4444

# ログレベル
LOG_LEVEL=INFO
```

### データベーススキーマ

data_sourceテーブルは以下の構造で作成してください：

```sql
CREATE TABLE data_source (
    id TEXT PRIMARY KEY NOT NULL,
    type TEXT NOT NULL,
    url TEXT,
    summary TEXT,
    published_at TIMESTAMP,
    raw_content TEXT,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- インデックス
CREATE INDEX data_source_type_idx ON data_source(type);
CREATE INDEX data_source_published_at_idx ON data_source(published_at DESC);
```

### 依存関係のインストール

```bash
uv sync
```

## 実行

### ローカル実行

```bash
# PostgreSQL接続あり
DATABASE_URL="postgresql://user:pass@localhost:5432/db" uv run python src/main.py

# PostgreSQL接続なし（JSONファイル出力）
uv run python src/main.py
```

### Railway環境

`railway.toml`の設定により、**5分間隔**で自動実行されます。

```toml
[deploy]
startCommand = "python src/main.py"
cronSchedule = "*/5 * * * *"  # 5分間隔実行
```

## アーキテクチャ

```
src/
├── models/         # データモデル (DataSource)
├── scrapers/       # サイト別スクレイパー実装
│   ├── base.py     # 基底スクレイパークラス
│   └── cryptopanic.py # CryptoPanic専用実装
├── storage/        # PostgreSQL永続化
├── utils/          # ログ設定などのユーティリティ
├── config.py       # 環境変数管理
├── webdriver.py    # Selenium WebDriver管理
├── constants.py    # 定数定義
└── main.py        # メインcronジョブ
```

## データフロー

1. **Config管理**で環境変数を安全に読み込み
2. **PostgreSQL storage**で前回実行時刻をチェック（効率化）
3. **Selenium WebDriver**でターゲットサイトにアクセス
4. **サイト別スクレイパー**でDOM解析・データ抽出
5. **DataSourceモデル**で型安全にデータ構造化
6. **差分フィルタリング**で新記事のみを抽出
7. **早期終了**で新記事がない場合はCPU節約
8. **PostgreSQL storage**でdata_sourceテーブルに保存
9. **重複チェック**でURL基準の重複を回避

## 新しいサイトの追加

新しいニュースサイトを追加する場合：

1. `src/scrapers/`に新しいスクレイパークラスを作成
2. `BaseScraper`を継承して必要なメソッドを実装
3. `src/main.py`にスクレイパー呼び出しを追加

例：
```python
# src/scrapers/coindesk.py
class CoinDeskScraper(BaseScraper):
    def get_source_name(self) -> str:
        return "coindesk"
    
    def get_base_url(self) -> str:
        return "https://www.coindesk.com/"
    
    def scrape_articles(self) -> list[DataSource]:
        # CoinDesk固有の実装
        pass
```

## 開発コマンド

```bash
# コード品質チェック
make check

# テスト実行
make test

# コードフォーマット
make format

# Selenium Grid起動（ローカル開発用）
make grid-up

# アプリケーション実行（ローカル）
make run
```

## 効率化機能

- **差分スクレイピング**: 前回実行時以降の新記事のみを処理
- **早期終了**: 新記事がない場合は即座に終了してCPU使用量を削減
- **接続プール**: PostgreSQL接続の効率的な管理
- **フォールバック保存**: DB接続失敗時の自動JSON出力
- **Railway最適化**: 環境変数の自動検出と適切な設定
