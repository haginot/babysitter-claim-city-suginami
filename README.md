# 杉並区ベビーシッター利用内訳書フォーム

## 概要
杉並区のベビーシッター（一時預かり）利用内訳書をWeb上で表示・印刷できるシンプルなアプリケーションです。

## 機能
- Google Docs風の印刷プレビュー機能
- A4サイズ対応の自動ページ分割
- JSONファイルからのデータ読み込み
- 印刷時の入力フィールド枠線非表示
- ズーム機能（50%〜150%）
- **NEW** PDFからテーブル抽出機能（pdfplumber使用）

## ディレクトリ構造
```
babysitter-claim-city-suginami/
├── frontend/                    # フロントエンド（HTMLファイル）
│   ├── babysitter-form.html     # 申請書フォーム
│   └── pdf-extractor.html       # PDF抽出ツール
├── backend/                     # バックエンド（Python API）
│   ├── app.py                   # Flask APIサーバー
│   ├── requirements.txt         # Python依存パッケージ
│   └── Dockerfile               # バックエンド用Dockerfile
├── data/                        # データファイル
│   └── form_data.json           # 申請書データ（直接編集）
├── docs/                        # ドキュメント
│   ├── template.pdf
│   └── sample.pdf
├── docker-compose.yml           # Docker設定
├── Dockerfile                   # Nginx用
├── nginx.conf                   # Webサーバー設定
├── start.sh                     # 起動スクリプト
└── README.md
```

## 使い方

### Docker を使用した起動（推奨）
```bash
# システムを起動
./start.sh

# またはDocker Composeを直接使用
docker-compose up -d

# システムを停止
docker-compose down
```

起動後、以下のURLにアクセスできます：
- 申請書フォーム: http://localhost:8081/frontend/babysitter-form.html
- PDF抽出ツール: http://localhost:8081/frontend/pdf-extractor.html
- または: http://localhost:8081/ （自動的にフォームにリダイレクト）

### 基本的な使い方

#### 申請書フォームの使い方
1. `data/form_data.json`ファイルを編集してデータを入力
2. ブラウザで http://localhost:8081/ を開く
3. 申請書が表示されます
4. 印刷ボタンをクリックして印刷

#### PDF抽出ツールの使い方
1. ブラウザで http://localhost:8081/frontend/pdf-extractor.html を開く
2. 請求書PDFファイルをアップロード（ドラッグ&ドロップまたはファイル選択）
3. 「テーブルを抽出」ボタンをクリック
4. 抽出されたテーブルがプレビュー表示されます
5. 必要に応じて、CSVでエクスポートまたはクリップボードにコピー

### データの編集方法
`data/form_data.json`ファイルを直接編集してください。ファイル保存後、ブラウザで「データ更新」ボタンをクリックすると、最新のデータが反映されます

#### form_data.json の構造
```json
{
  "year": "7",                    // 令和年度
  "applicantName": "申請者名",
  "childName": "児童名",
  "month": "4",                   // 月
  "page1": {
    "rows": [                     // 利用記録（最大10行）
      {
        "date": "1",              // 利用日
        "dayTime": "9:00 ～ 10:00",     // 日中利用時間
        "dayDuration": "1時間00分",      // 日中利用時間数
        "nightTime": "",                 // 夜間利用時間
        "nightDuration": "",             // 夜間利用時間数
        "amount": "2,500"                // 実支払額
      }
    ],
    "dayTotalTime": "5時間00分",
    "nightTotalTime": "",
    "totalAmount": "13,000",
    "dayHours": "5",
    "nightHours": "0",
    "subsidyAmount": "12,500",
    "requestAmount": "12,500",
    "usageHours": "5"
  },
  "page2": {                      // 複数月の場合（オプション）
    "table1": { /* ... */ },
    "table2": { /* ... */ }
  }
}
```

### キーボードショートカット
- `Ctrl/Cmd + P`: 印刷
- `Ctrl/Cmd + D`: ページ分割
- `Ctrl/Cmd + R`: データ更新

## ファイル構成
- `frontend/babysitter-form.html` - 申請書フォーム（Google Docs風印刷プレビュー機能付き）
- `data/form_data.json` - フォームデータ（直接編集）
- `docs/template.pdf` - 元のPDFテンプレート
- `docs/sample.pdf` - 記入例

## 本番環境へのデプロイ（無料）

### Renderでのデプロイ（推奨）

Renderを使用すると、無料で本アプリケーションを公開できます。

**デプロイ手順:**

1. **GitHubにプッシュ**
   ```bash
   git push origin main
   ```

2. **Renderアカウント作成**
   - [Render](https://render.com)でアカウント作成
   - GitHubアカウントで連携

3. **自動デプロイ**
   - "New" → "Blueprint" を選択
   - このリポジトリを選択
   - `render.yaml`が自動検出されて、2つのサービスがデプロイされます:
     - `babysitter-api` (Flask API)
     - `babysitter-frontend` (Nginx)

4. **API URLを設定**
   - フロントエンドサービスの環境変数に以下を追加:
     ```
     API_URL=https://babysitter-api.onrender.com
     ```
   - `frontend/pdf-extractor.html`と`frontend/json-editor.html`のAPI URLを更新

5. **アクセス**
   - `https://babysitter-frontend.onrender.com` にアクセス

**注意事項:**
- 無料プランは15分間アクセスがないとスリープします
- 初回アクセス時は起動に30秒程度かかります
- 月に750時間まで無料で利用可能

### その他のデプロイオプション

#### Railway
1. [Railway](https://railway.app)でアカウント作成
2. GitHubリポジトリをインポート
3. 自動的にDocker Composeを検出してデプロイ
4. 月$5相当の無料クレジットあり

#### Fly.io
1. [Fly.io](https://fly.io)でアカウント作成（クレジットカード登録必要）
2. `flyctl`をインストール
3. `flyctl launch`でデプロイ
4. 無料プランで3つのアプリまで

## 注意事項
- `data/form_data.json`ファイルは削除されました。PDFアップロードから開始してください
- Dockerを使用した起動を推奨します（./start.sh）
- ローカルでの単体起動の場合は、簡易的なWebサーバーを使用してください：
  ```bash
  # Python 3の場合
  python -m http.server 8000

  # その後、http://localhost:8000/frontend/pdf-extractor.html にアクセス
  ```