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
- **新機能：テーブル編集機能**
  - 請求書CSVデータのリアルタイム編集
  - 行の追加・削除
  - データ検証・バックアップ機能
  - 申請書フォームとの連携

## ディレクトリ構造
```
babysitter-claim-city-suginami/
├── frontend/              # フロントエンド（HTMLファイル）
│   ├── babysitter-form.html
│   ├── babysitter-form-with-print.html
│   └── table-editor.html        # テーブル編集画面
├── backend/               # バックエンド（変換スクリプト・API）
│   ├── invoice_to_form_converter.py
│   ├── csv_api_server.py         # CSV操作APIサーバー
│   ├── requirements.txt          # Python依存関係
│   └── Dockerfile               # APIサーバー用Docker設定
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
- テーブル編集画面: http://localhost:8080/frontend/table-editor.html
- 申請書フォーム: http://localhost:8080/frontend/babysitter-form.html
- 印刷用フォーム: http://localhost:8080/frontend/babysitter-form-with-print.html
- API サーバー: http://localhost:5001/api/

### 基本的な使い方
1. `frontend/babysitter-form.html`をブラウザで開く（Google Docs風印刷プレビュー機能付き）
2. 必要な情報を入力
3. 印刷ボタンをクリックして印刷

### テーブル編集機能の使い方
1. `frontend/table-editor.html`をブラウザで開く
2. 「データ読み込み」ボタンでCSVファイルを読み込み
3. テーブル内でデータを直接編集
4. 「行追加」ボタンで新しい行を追加
5. 「データ保存」ボタンで変更を保存
6. 「プレビュー」ボタンで申請書フォームへの変換内容を確認
7. 「申請書フォームへ」ボタンで申請書フォームに移動・データ反映

### データ連携機能
編集したテーブルデータは自動的に申請書フォーム形式に変換されます：
- **申請者名・児童名**: お子さま情報から自動抽出
- **年度・月**: 利用日から自動計算（令和年度に変換）
- **利用時間**: 開始・終了時刻から日中・夜間利用時間を自動計算
- **合計金額**: 全利用分の合計を自動計算
- **データ検証**: 必須項目・フォーマットの自動チェック

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
- `frontend/babysitter-form.html` - メインのHTMLファイル（Google Docs風印刷プレビュー機能付き）
- `frontend/babysitter-form-with-print.html` - 印刷用フォーム（旧版）
- `frontend/table-editor.html` - テーブル編集画面
- `data/form-data.json` - フォームの初期データ（オプション）
- `docs/template.pdf` - 元のPDFテンプレート
- `docs/sample.pdf` - 記入例
- `backend/invoice_to_form_converter.py` - 請求書データ変換スクリプト
- `backend/csv_api_server.py` - CSV操作APIサーバー

## 注意事項
- `data/form-data.json`ファイルが存在しない場合は、空のフォームが表示されます
- Dockerを使用した起動を推奨します（./start.sh）
- ローカルでの単体起動の場合は、簡易的なWebサーバーを使用してください：
  ```bash
  # Python 3の場合
  python -m http.server 8000
  
  # その後、http://localhost:8000/frontend/babysitter-form.html にアクセス
  ```