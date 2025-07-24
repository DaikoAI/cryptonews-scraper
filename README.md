# Python Railway Template - Selenium Standalone Chromium

Selenium Standalone Chromium を使用した Remote WebDriver スクレイピングアプリケーションのテンプレートです。

## 🚀 特徴

- **Selenium Standalone Chromium**: 安定したローカル Docker 環境
- **Remote WebDriver**: スケーラブルな分離アーキテクチャ
- **ARM64 (M1 Mac) 対応**: seleniarm イメージを使用
- **色付きログ**: ANSI色とアイコンによる美しいログ出力
- **モジュラー設計**: 保守性の高いコード構造
- **定数管理**: 一元的な設定値管理
- **汎用的なスクレイパークラス**: 再利用可能な WebDriver 管理

## 📁 プロジェクト構造

```
src/
├── main.py              # メインエントリーポイント
├── scraper.py           # WebDriver管理クラスとスクレイピング関数
├── constants.py         # 定数管理（設定値、メッセージ等）
├── utils/
│   └── logger.py        # 色付きロガー
├── __init__.py
tests/
└── test_main.py         # テストファイル
docker-compose.yaml      # ローカル開発専用 Selenium Standalone構成
Dockerfile               # Railway本番デプロイ用コンテナ
railway.toml             # Railway設定ファイル（Cron等）
Makefile                 # 便利なコマンド集
```

## 🎯 設計思想

### クラス設計の分離
- **`StandaloneChromiumScraper`**: WebDriverの管理に特化した汎用クラス
  - 接続・切断の管理
  - 基本的なWebDriver操作（`get_page`, `find_element`, `take_screenshot`など）
  - Context Managerによる安全なリソース管理

- **外部関数**: 特定の業務ロジック
  - `scrape_test_page()`: テストページ固有のスクレイピングロジック
  - クラスとビジネスロジックの責任分離

### 定数管理
- **`constants.py`**: 全ての設定値を一箇所で管理
  - Selenium設定（URL、ブラウザ、タイムアウト）
  - ブラウザオプション（ウィンドウサイズ、User-Agent）
  - ログ設定（色、アイコン、ANSI制御コード）
  - メッセージテンプレート（エラー、成功メッセージ）

## 🛠️ 使用方法

### 基本使用例

```python
from scraper import StandaloneChromiumScraper, scrape_test_page

# 汎用的なWebDriver管理
with StandaloneChromiumScraper() as scraper:
    # ページ取得
    scraper.get_page("https://example.com")
    
    # 要素検索
    element = scraper.find_element(By.TAG_NAME, "h1")
    
    # ページ情報取得
    page_info = scraper.get_page_info()
    
    # スクリーンショット
    scraper.take_screenshot("example.png")

# 特定の業務ロジック
with StandaloneChromiumScraper() as scraper:
    result = scrape_test_page(scraper)
    print(result)
```

### Docker での実行（ローカル開発専用）

**⚠️ 注意**: `docker-compose` はローカル開発専用です。Railway本番環境では使用できません。

```bash
# スクレイピング実行（Selenium起動 + アプリ実行 + ログ表示）
make scrape

# Selenium Standalone のみ起動
make start-selenium

# ログ表示
make logs

# 環境クリーンアップ
make clean       # Python + Docker リソース削除
make clean-all   # 全Docker リソース完全削除（注意）
```

### ローカル開発

```bash
# 依存関係インストール
uv sync

# Python実行
python -m src.main
```

## ⚙️ 設定

### 環境変数

```bash
SELENIUM_BROWSER=chrome          # chrome または firefox
SELENIUM_REMOTE_URL=http://selenium:4444  # Docker環境
# SELENIUM_REMOTE_URL=http://localhost:4444  # ローカル環境
```

### ブラウザオプション

`src/constants.py` で設定をカスタマイズ:

```python
# Chrome設定
CHROME_WINDOW_SIZE = "1920,1080"
CHROME_USER_AGENT = "Mozilla/5.0 ..."

# Firefox設定  
FIREFOX_WINDOW_WIDTH = "1920"
FIREFOX_WINDOW_HEIGHT = "1080"

# タイムアウト
DEFAULT_TIMEOUT = 10  # 秒
```

## 🔧 カスタマイズ

### 新しいスクレイピング関数の追加

```python
def scrape_custom_site(scraper: StandaloneChromiumScraper) -> dict:
    """カスタムサイトのスクレイピング"""
    scraper.get_page("https://custom-site.com")
    scraper.wait_for_element(By.CLASS_NAME, "content")
    
    # 業務ロジック
    data = {}
    elements = scraper.find_elements(By.CSS_SELECTOR, ".item")
    for element in elements:
        data[element.get_attribute("id")] = element.text
    
    return data
```

### 定数の追加

```python
# constants.py に追加
CUSTOM_SITE_URL = "https://custom-site.com"
CUSTOM_TIMEOUT = 15
CUSTOM_ERROR_MSG = "Custom site scraping failed: {}"
```

## 📊 ログ出力

色付きログで実行状況を視覚的に確認:

```
✅ 2025-01-23 12:23:51 - INFO - Connected successfully! Browser: chrome 124.0
🕷️ 2025-01-23 12:23:51 - INFO - Navigating to: https://httpbin.org/html  
📸 2025-01-23 12:23:54 - INFO - Screenshot saved: reports/test_screenshot.png
✅ 2025-01-23 12:23:54 - INFO - Test completed successfully!
```

## 🧪 テスト

```bash
# Docker内でテスト実行
docker run --rm python-railway-template-selenium-scraper python -m pytest tests/ -v

# ローカルでテスト実行
uv run pytest tests/ -v
```

## 🚢 Railway デプロイ

### ⚠️ 重要: Railway は docker-compose をサポートしていません
Railwayでは単一のDockerfileのみサポートされており、docker-composeでの複数サービス構成はできません。
**docker-compose.yaml はローカル開発専用**で、Railway本番環境では使用できません。
そのため、**ダッシュボードから手動でデプロイ**する必要があります。

### 📋 手動デプロイ手順（ダッシュボード）

#### 1. 🚀 プロジェクト作成
1. [Railway Dashboard](https://railway.app/dashboard) にアクセス
2. `+ New Project` または `⌘K` をクリック
3. **`Empty project`** を選択（GitHub repoは後で設定）
4. プロジェクト名を分かりやすい名前に変更
   - Settings → Project Name → 例: `selenium-scraper`

#### 2. 🔧 サービス作成
1. `+ Create` ボタンから **`Empty service`** を作成
2. サービス名を設定（右クリック → Rename）
   - 例: `scraper-app` 
3. `Deploy` ボタンまたは `⇧ Enter` でサービス作成

#### 3. 📂 リポジトリ接続
1. **Service Settings** を開く
2. **Source** セクションで `Connect Repo` をクリック
3. GitHub連携（初回のみ）後、対象リポジトリを選択
4. **Branch**: `main` を選択
5. **Root Directory**: 空欄のまま（プロジェクトルート）

#### 4. ⚙️ 環境変数設定
1. **Variables** タブを開く
2. 以下の環境変数を追加:

| Variable Name | Value | 説明 |
|---------------|-------|------|
| `SELENIUM_BROWSER` | `chrome` | ブラウザ指定 |
| `SELENIUM_REMOTE_URL` | `http://localhost:4444` | ローカルSelenium（無視される） |

**注意**: RailwayではSelenium Standaloneコンテナが使用できないため、
ローカル開発用の設定値として記載しています。

#### 5. 🚀 デプロイ実行
1. **Deployments** タブで `Deploy` ボタンをクリック
2. ビルドログを確認して正常終了を確認
3. 初回デプロイには数分かかります

#### 6. 🕐 Cron スケジュール設定
1. **Settings** タブを開く  
2. **Cron Schedule** セクションで設定:
   ```
   */10 * * * *
   ```
   （10分間隔で実行）
3. **Restart Policy**: `NEVER` を選択
   - 一度実行完了後は次のCron実行まで停止

### 🔧 railway.toml 設定ファイル

プロジェクトルートに `railway.toml` を作成して設定を管理:

```toml
[build]
builder = "dockerfile"

[deploy]
startCommand = "app"  # pyproject.tomlで定義されたエントリーポイント
restartPolicyType = "NEVER"  # Cronジョブとして実行

[[services]]
[services.app]
source = "/"

# Cron設定（10分間隔）
[services.app.cron]
schedule = "*/10 * * * *"
```

### 📊 デプロイ確認

#### ✅ 成功確認項目
1. **Build Success**: Dockerfileビルドが正常完了
2. **Environment Detection**: ログで `Environment: railway` 表示
3. **Cron Execution**: 指定時間に自動実行される
4. **Exit Code 0**: スクレイピング処理が正常終了

#### 🔍 デバッグ方法
1. **Deployments** タブでログ確認
2. **Metrics** でリソース使用状況確認  
3. **Settings** → **Variables** で環境変数確認

### 🚨 よくある問題と解決方法

#### 1. `uv: command not found`
- **原因**: Dockerfileでuv実行が失敗
- **解決**: `CMD ["app"]` でPythonスクリプト直接実行

#### 2. `selenium module not found`  
- **原因**: 依存関係インストール失敗
- **解決**: `uv sync --frozen` でロックファイル通りにインストール

#### 3. Selenium接続エラー
- **原因**: RailwayでSelenium Standaloneが利用不可
- **現状**: このテンプレートは**ローカル開発専用**
- **対応**: 外部Seleniumサービス（Browserless等）への移行が必要

### 💡 運用のコツ

#### Cron ジョブ監視
```bash
# Railway CLIでログ確認
railway logs --follow

# 特定デプロイメントのログ確認  
railway logs <deployment-id>
```

#### 本番環境での考慮事項
1. **スケーリング**: Cronジョブは基本的にシングルインスタンス
2. **エラーハンドリング**: 失敗時の通知設定を検討
3. **ログ保持**: Railway無料プランはログ保持期間制限あり
4. **コスト管理**: 実行頻度とリソース使用量の最適化

### 🔄 アップデート手順
1. GitHubにコード変更をプッシュ
2. Railwayで自動的に新しいデプロイメントが開始
3. **Deployments** タブで進行状況確認
4. 次回Cron実行で新バージョンが動作

**👆 このようにRailwayでは docker-compose は使えないため、ダッシュボードでの手動設定が必要です！**

## 🔍 トラブルシューティング

### よくある問題

1. **接続エラー**: Selenium Standalone が起動しているか確認
   ```bash
   docker-compose up selenium-chrome
   ```

2. **ARM64 (M1 Mac) での問題**: `seleniarm` イメージを使用
   ```yaml
   # docker-compose.yml
   image: seleniarm/standalone-chromium:latest
   ```

3. **要素が見つからない**: 適切な待機を追加
   ```python
   scraper.wait_for_element(By.ID, "target-element")
   ```

4. **Docker ビルドエラー**: キャッシュクリアで解決
   ```bash
   make clean        # プロジェクト関連削除
   make clean-all    # 全Docker リソース削除（注意）
   ```

5. **ポート競合エラー**: 既存コンテナの停止
   ```bash
   make clean-docker  # Dockerリソースのみ削除
   ```

### 設定確認

```bash
# Selenium Grid 状態確認
curl http://localhost:4444/wd/hub/status

# VNC で画面確認 
open vnc://localhost:5900
```

## 📄 ライセンス

MIT License

## 🤝 貢献

1. Fork the project
2. Create your feature branch
3. Commit your changes  
4. Push to the branch
5. Open a Pull Request
