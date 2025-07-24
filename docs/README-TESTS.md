# テストドキュメント

## テスト概要

CryptoPanic Scraperのテストスイートでは以下の主要コンポーネントをテストします：

## テスト構成

### 1. `tests/test_models.py` - DataSourceモデルテスト
- **基本的なインスタンス作成**
- **全フィールド指定での作成**
- **バリデーション（is_valid）**
- **辞書変換（to_dict）**
- **CryptoPanicニュースからの作成（from_cryptopanic_news）**
- **文字列表現（__repr__）**

### 2. `tests/test_config.py` - 設定管理テスト
- **環境変数からの読み込み**
- **デフォルト値の確認**
- **Railway環境判定**
- **Selenium Remote URL取得**
- **設定バリデーション**
- **Railway環境でのDATABASE_URL必須チェック**

### 3. `tests/test_scrapers.py` - CryptoPanicスクレイパーテスト
- **ソース名・ベースURL取得**
- **ページ読み込み待機（成功・タイムアウト）**
- **記事要素取得（成功・フォールバック）**
- **タイトル・URL抽出**
- **公開日時抽出（成功・フォールバック）**
- **通貨抽出**
- **ソースドメイン抽出**
- **URL正規化**
- **DataSource抽出（成功・失敗）**

## テスト実行

```bash
# 全テスト実行
make test

# 特定のテストファイル実行
uv run python -m pytest tests/test_models.py -v

# 特定のテストケース実行
uv run python -m pytest tests/test_models.py::TestDataSource::test_create_basic_data_source -v

# カバレッジ付きテスト実行
uv run python -m pytest tests/ --cov=src --cov-report=html
```

## モック戦略

### WebDriverのモック
- Seleniumの`WebDriver`インスタンスをモック
- HTML要素取得をシミュレート
- ページナビゲーションのモック

### 環境変数のモック
- `@patch.dict(os.environ)`でテスト環境を分離
- Railway/開発環境の切り替えテスト

### 時刻のモック
- 公開日時パースのテスト
- フォールバック動作の確認

## テストデータ

### MockWebElement
CryptoPanicのHTML構造をシミュレートするモッククラス：

```python
class MockWebElement:
    def __init__(self, text="", href="", datetime_attr="", class_attr=""):
        self.text = text
        self._href = href
        self._datetime = datetime_attr
        self._class = class_attr
```

### テスト用DataSource
```python
ds = DataSource.from_cryptopanic_news(
    title="Bitcoin Price Surges",
    url="https://cryptopanic.com/news/12345",
    published_at=datetime(2025, 1, 24, 12, 0, 0, tzinfo=timezone.utc),
    currencies=["BTC", "ETH"],
    source_domain="coindesk.com",
    scraped_at=datetime.now(UTC),
)
```

## CI/CD統合

### make checkとmake test
```bash
# コード品質チェック
make check    # ruffによるlinting

# テスト実行
make test     # pytest実行
```

### パフォーマンス考慮
- SeleniumのWebDriverモック化により高速実行
- データベース接続をモック化
- ネットワーク通信なしのユニットテスト

## テストカバレッジ目標

- **DataSourceモデル**: 100%
- **Config設定管理**: 95%以上
- **CryptoPanicスクレイパー**: 90%以上
- **全体**: 85%以上

## 注意事項

1. **deprecation warnings**: `datetime.utcnow()`は`datetime.now(UTC)`に更新済み
2. **環境分離**: テスト間で環境変数が影響しないよう`clear=True`使用
3. **モック精度**: 実際のCryptoPanic HTML構造に近いモック作成 