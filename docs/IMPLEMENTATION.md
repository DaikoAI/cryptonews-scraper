# CryptoPanic Scraper Implementation

## data_sourceテーブル対応実装

### 変更概要

1. **NewsArticle → DataSource モデル移行**
   - `NewsArticle`から`DataSource`モデルに完全移行
   - `data_source`テーブルスキーマに完全対応

2. **target.html 構造対応**
   - CryptoPanicの実際のHTML構造に対応
   - `.news-row`、`.nc-title`、`.nc-date`、`.nc-currency`セレクター使用

3. **差分スクレイピング実装**
   - 前回取得した最新記事の公開日時を取得
   - 新しい記事のみをフィルタリング
   - 更新がない場合はスキップ

4. **1分間隔cron対応**
   - `cron-schedule.py`スクリプト追加
   - `crontab-config`設定ファイル追加

### ファイル構造

```
src/
├── models/
│   ├── data_source.py          # 新: DataSourceモデル
│   └── news_article.py         # 既存: 後方互換性のため維持
├── scrapers/
│   ├── cryptopanic.py          # 更新: target.html構造対応
│   └── base.py                 # 更新: DataSource対応
├── storage/
│   └── postgres_storage.py     # 更新: DataSource対応
├── webdriver.py                # 旧core/から移動
└── main.py                     # 更新: 差分スクレイピング対応

cron-schedule.py                # 新: cronジョブスクリプト
crontab-config                  # 新: cron設定例
```

### データフロー

1. **前回取得チェック**
   ```sql
   SELECT MAX(published_at) FROM data_source 
   WHERE type = 'news' AND published_at IS NOT NULL
   ```

2. **CryptoPanicスクレイピング**
   - `.news-row.news-row-link`要素を取得
   - タイトル、URL、公開日時、通貨を抽出

3. **差分フィルタリング**
   - `published_at > last_published_at`の記事のみ
   - 公開日時不明の場合は新規として扱う

4. **data_source保存**
   ```sql
   INSERT INTO data_source (
       id, type, url, summary, published_at, raw_content, created_at
   ) VALUES (?, 'news', ?, ?, ?, ?, ?)
   ```

### raw_content構造

```json
{
  "source": "cryptopanic",
  "scraped_at": "2025-01-24T12:00:00",
  "currencies": ["BTC", "ETH"],
  "source_domain": "coindesk.com"
}
```

### cron設定

```bash
# 1分間隔実行
* * * * * cd /path/to/cryptonews-scraper && python3 cron-schedule.py

# 5分間隔実行（テスト用）
*/5 * * * * cd /path/to/cryptonews-scraper && python3 cron-schedule.py
```

### テスト手順

1. **手動実行テスト**
   ```bash
   DATABASE_URL="postgresql://..." python src/main.py
   ```

2. **cronスクリプトテスト**
   ```bash
   python cron-schedule.py
   ```

3. **スクレイピング対象確認**
   - `docs/target.html`の構造確認
   - セレクターの動作確認 