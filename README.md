# 杉並区ベビーシッター利用内訳書フォーム

## 概要
杉並区のベビーシッター（一時預かり）利用内訳書をWeb上で入力・印刷できるHTMLフォームです。

## 機能
- Google Docs風の印刷プレビュー機能
- A4サイズ対応の自動ページ分割
- JSONファイルからのデータ読み込み
- 印刷時の入力フィールド枠線非表示
- ズーム機能（50%〜150%）
- 請求書CSVデータから申請書フォーマットへの変換（Python）

## ディレクトリ構造
```
babysitter-claim-city-suginami/
├── frontend/              # フロントエンド（HTMLファイル）
│   ├── babysitter-form.html
│   └── babysitter-form-with-print.html
├── backend/               # バックエンド（変換スクリプト）
│   └── invoice_to_form_converter.py
├── data/                  # データファイル
│   ├── form-data.json
│   ├── converted_form_data.json
│   ├── invoice-data.csv
│   └── invoice-data_converted.json
├── assets/                # 静的ファイル
│   ├── images/
│   │   └── samples/
│   └── templates/
├── docs/                  # ドキュメント
│   ├── template.pdf
│   └── sample.pdf
├── docker-compose.yml     # Docker設定
├── Dockerfile
├── nginx.conf
└── README.md
```

## 使い方

### 基本的な使い方
1. `frontend/babysitter-form-with-print.html`をブラウザで開く
2. 必要な情報を入力
3. 印刷ボタンをクリックして印刷

### JSONデータの読み込み
フォームの初期値を自動的に読み込むには：

1. `data/form-data.json`ファイルを編集して、必要なデータを入力
2. HTMLファイルを開くと、自動的にJSONファイルからデータが読み込まれます

#### form-data.jsonの構造
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
    ]
  }
}
```

### キーボードショートカット
- `Ctrl/Cmd + P`: 印刷
- `Ctrl/Cmd + ,`: 設定パネルの開閉
- `Ctrl/Cmd + D`: ページ分割

## ファイル構成
- `frontend/babysitter-form-with-print.html` - メインのHTMLファイル
- `data/form-data.json` - フォームの初期データ（オプション）
- `docs/template.pdf` - 元のPDFテンプレート
- `docs/sample.pdf` - 記入例
- `backend/invoice_to_form_converter.py` - 請求書データ変換スクリプト

## 注意事項
- `data/form-data.json`ファイルが存在しない場合は、空のフォームが表示されます
- ブラウザのセキュリティ設定により、ローカルファイルの読み込みが制限される場合があります。その場合は、簡易的なWebサーバーを使用してください：
  ```bash
  # Python 3の場合
  python -m http.server 8000
  
  # その後、http://localhost:8000/frontend/babysitter-form-with-print.html にアクセス
  ```