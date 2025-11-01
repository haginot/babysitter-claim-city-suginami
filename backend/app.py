from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import os

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/api/extract-table', methods=['POST'])
def extract_table():
    """
    PDFファイルの1ページ目から「ご利用日」ヘッダーを含むテーブルを抽出する
    """
    try:
        # ファイルの取得
        if 'file' not in request.files:
            return jsonify({"error": "ファイルがアップロードされていません"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "ファイル名が空です"}), 400

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "PDFファイルのみアップロード可能です"}), 400

        # PDFを読み込み
        pdf_bytes = file.read()
        pdf_file = io.BytesIO(pdf_bytes)

        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) == 0:
                return jsonify({"error": "PDFにページがありません"}), 400

            # 1ページ目を取得
            first_page = pdf.pages[0]

            # テーブルを抽出
            tables = first_page.extract_tables()

            if not tables:
                return jsonify({"error": "テーブルが見つかりませんでした"}), 404

            # デバッグ用：すべてのテーブルをクリーンアップ
            debug_tables = []
            for table_idx, table in enumerate(tables):
                if table:
                    cleaned = []
                    for row in table:
                        if row:
                            cleaned_row = []
                            for cell in row:
                                if cell:
                                    # 改行を削除してスペースに置き換え
                                    cell_str = str(cell).replace('\n', ' ').replace('\r', ' ').strip()
                                    cell_str = ' '.join(cell_str.split())
                                    cleaned_row.append(cell_str)
                                else:
                                    cleaned_row.append("")
                            cleaned.append(cleaned_row)
                    debug_tables.append({
                        "table_index": table_idx,
                        "rows": len(cleaned),
                        "columns": len(cleaned[0]) if cleaned else 0,
                        "data": cleaned
                    })

            # すべてのテーブルから「ご利用日」セルを探索
            # 複数見つかった場合は最も短い（最も具体的な）セルを選ぶ
            target_table = None
            target_row_idx = None
            target_col_idx = None
            min_cell_length = float('inf')

            for table in tables:
                if not table or len(table) == 0:
                    continue

                # テーブル全体を探索して「ご利用日」を探す
                # 複数のバリエーションに対応（全角/半角、異体字など）
                for row_idx, row in enumerate(table):
                    if not row:
                        continue

                    for col_idx, cell in enumerate(row):
                        if cell:
                            cell_str = str(cell).strip()
                            # 「ご利用日」の様々なバリエーションをチェック
                            # Unicode正規化やスペース削除も考慮
                            normalized_cell = cell_str.replace(' ', '').replace('　', '')

                            if ('ご利用日' in normalized_cell or
                                'ご利⽤⽇' in normalized_cell or  # 縦書き用文字
                                '利用日' in normalized_cell or
                                '利⽤⽇' in normalized_cell):
                                # 最も短いセルを優先（PDF全文ではなく、ヘッダーセルを選ぶため）
                                cell_length = len(normalized_cell)
                                if cell_length < min_cell_length:
                                    target_table = table
                                    target_row_idx = row_idx
                                    target_col_idx = col_idx
                                    min_cell_length = cell_length

            if not target_table:
                # デバッグ情報を含めてエラーを返す
                return jsonify({
                    "error": "「ご利用日」を含むテーブルが見つかりませんでした",
                    "debug": {
                        "tables_found": len(tables),
                        "all_tables": debug_tables
                    }
                }), 404

            # 「ご利用日」が含まれる行をヘッダー行として、その行から抽出を開始
            # 「ご利用日」が含まれる列から右側のみを抽出
            trimmed_table = []

            # target_row_idx行目（ヘッダー行）から下をすべて抽出
            for row in target_table[target_row_idx:]:
                if row and len(row) > target_col_idx:
                    # target_col_idx列目から右側を抽出
                    trimmed_row = row[target_col_idx:]
                    trimmed_table.append(trimmed_row)

            # 空行と「合計」行を削除
            filtered_table = []
            for row in trimmed_table:
                if not row or not any(cell for cell in row):
                    continue  # 空行をスキップ

                # 行内のすべてのセルを結合して「合計」が含まれているかチェック
                row_text = ''.join([str(cell).replace(' ', '').replace('　', '') for cell in row if cell])

                # 「合計」が含まれる行はスキップ
                if '合計' in row_text or '⼩計' in row_text:
                    continue

                filtered_table.append(row)

            if not filtered_table:
                return jsonify({"error": "テーブルのトリミングに失敗しました"}), 500

            trimmed_table = filtered_table

            # ヘッダー行（最初の行）が「ご利用日」で始まることを確認
            if trimmed_table and trimmed_table[0]:
                first_cell = str(trimmed_table[0][0]).strip() if trimmed_table[0][0] else ""
                normalized_first = first_cell.replace(' ', '').replace('　', '')
                if not any(keyword in normalized_first for keyword in ['ご利用日', 'ご利⽤⽇', '利用日', '利⽤⽇']):
                    return jsonify({"error": "ヘッダー行の検証に失敗しました"}), 500

            # Noneを空文字列に変換し、改行を削除
            cleaned_table = []
            for row in trimmed_table:
                if row:
                    cleaned_row = []
                    for cell in row:
                        if cell:
                            # 改行を削除してスペースに置き換え、前後の空白を削除
                            cell_str = str(cell).replace('\n', ' ').replace('\r', ' ').strip()
                            # 連続する空白を1つにまとめる
                            cell_str = ' '.join(cell_str.split())
                            cleaned_row.append(cell_str)
                        else:
                            cleaned_row.append("")
                    cleaned_table.append(cleaned_row)
                else:
                    cleaned_table.append([])

            return jsonify({
                "success": True,
                "table": cleaned_table,
                "rows": len(cleaned_table),
                "columns": len(cleaned_table[0]) if cleaned_table and cleaned_table[0] else 0
            })

    except Exception as e:
        return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500

@app.route('/api/convert-to-json', methods=['POST'])
def convert_to_json():
    """
    抽出されたテーブルデータをform_data.json形式に変換する
    """
    try:
        data = request.json
        if not data or 'table' not in data:
            return jsonify({"error": "テーブルデータが必要です"}), 400

        table = data['table']
        if len(table) < 2:  # ヘッダー + 最低1行のデータ
            return jsonify({"error": "データ行が必要です"}), 400

        # ヘッダー行をスキップしてデータ行のみを取得
        rows = table[1:]

        # 月ごとにデータをグループ化
        monthly_data = {}

        for row in rows:
            if len(row) < 14:
                continue

            # 日付から月を抽出（例: "2025/07/12" -> "7"）
            date_str = row[0]
            if not date_str or '/' not in date_str:
                continue

            parts = date_str.split('/')
            if len(parts) < 3:
                continue

            month = parts[1].lstrip('0')  # "07" -> "7"
            day = parts[2].lstrip('0')    # "12" -> "12"

            # 時間を抽出
            start_time = row[1]  # "10:00"
            end_time = row[2]    # "15:45"

            # 助成対象金額を抽出（カンマを削除）
            subsidy_amount_str = row[13].replace(',', '')
            try:
                subsidy_amount = int(subsidy_amount_str) if subsidy_amount_str else 0
            except:
                subsidy_amount = 0

            # 時間計算（簡易版）
            day_time = f"{start_time} ～ {end_time}"

            # 時間数を計算
            try:
                start_h, start_m = map(int, start_time.split(':'))
                end_h, end_m = map(int, end_time.split(':'))
                total_minutes = (end_h * 60 + end_m) - (start_h * 60 + start_m)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                day_duration = f"{hours}時間{minutes:02d}分"
            except:
                day_duration = ""
                total_minutes = 0

            # 月ごとのデータに追加
            if month not in monthly_data:
                monthly_data[month] = []

            monthly_data[month].append({
                "date": day,
                "dayTime": day_time,
                "dayDuration": day_duration,
                "nightTime": "",
                "nightDuration": "",
                "amount": f"{subsidy_amount:,}",
                "subsidy_amount": subsidy_amount,
                "day_minutes": total_minutes,
                "night_minutes": 0
            })

        # 月を昇順にソート
        sorted_months = sorted(monthly_data.keys(), key=lambda x: int(x))

        if not sorted_months:
            return jsonify({"error": "有効なデータが見つかりませんでした"}), 400

        # form_data.json形式に変換
        result = {
            "year": "7",  # デフォルト値（令和7年）
            "applicantName": "杉並 なみ",  # デフォルト値
            "childName": "杉並 すけ",  # デフォルト値
            "month": sorted_months[0]
        }

        # 最初の月のデータをpage1に
        first_month = sorted_months[0]
        first_month_rows = monthly_data[first_month]

        day_total_minutes = sum(r['day_minutes'] for r in first_month_rows)
        night_total_minutes = sum(r['night_minutes'] for r in first_month_rows)
        day_total_hours = day_total_minutes // 60
        day_total_mins = day_total_minutes % 60
        night_total_hours = night_total_minutes // 60
        night_total_mins = night_total_minutes % 60
        total_amount = sum(r['subsidy_amount'] for r in first_month_rows)

        # 全月の合計を計算（page1の他ページ含む総計用）
        all_day_minutes = 0
        all_night_minutes = 0
        all_total_amount = 0
        for month in sorted_months:
            month_rows = monthly_data[month]
            all_day_minutes += sum(r['day_minutes'] for r in month_rows)
            all_night_minutes += sum(r['night_minutes'] for r in month_rows)
            all_total_amount += sum(r['subsidy_amount'] for r in month_rows)

        all_day_hours = all_day_minutes // 60
        all_day_mins = all_day_minutes % 60
        all_night_hours = all_night_minutes // 60
        all_night_mins = all_night_minutes % 60

        # 補助基準額の計算: 日中利用時間 × 2500円 + 夜間利用時間 × 3500円
        calculated_subsidy_amount = (all_day_hours * 2500) + (all_night_hours * 3500)

        # 交付請求額は補助基準額と実際の合計金額の小さい方
        request_amount = min(calculated_subsidy_amount, all_total_amount)

        result["page1"] = {
            "rows": first_month_rows,
            "dayTotalTime": f"{day_total_hours}時間{day_total_mins:02d}分",
            "nightTotalTime": f"{night_total_hours}時間{night_total_mins:02d}分" if night_total_hours > 0 else "",
            "totalAmount": f"{total_amount:,}",
            # 以下は全月の合計を使用（補助基準額の計算に使用）
            "dayHours": str(all_day_hours),
            "nightHours": str(all_night_hours),
            "subsidyAmount": f"{calculated_subsidy_amount:,}",
            "requestAmount": f"{request_amount:,}",
            "usageHours": str(all_day_hours + all_night_hours),
            "grandTotalDayTime": f"{all_day_hours}時間{all_day_mins:02d}分",
            "grandTotalNightTime": f"{all_night_hours}時間{all_night_mins:02d}分" if all_night_hours > 0 else "",
            "grandTotalAmount": f"{all_total_amount:,}"
        }

        # 2番目以降の月がある場合はpage2に
        if len(sorted_months) > 1:
            result["page2"] = {
                "grandTotal": {
                    "totalDayHours": str(all_day_hours),
                    "totalNightHours": str(all_night_hours),
                    "totalSubsidyAmount": f"{calculated_subsidy_amount:,}",
                    "totalRequestAmount": f"{request_amount:,}",
                    "totalUsageHours": str(all_day_hours + all_night_hours)
                }
            }

            for idx, month in enumerate(sorted_months[1:], start=1):
                month_rows = monthly_data[month]
                month_day_minutes = sum(r['day_minutes'] for r in month_rows)
                month_night_minutes = sum(r['night_minutes'] for r in month_rows)
                month_day_hours = month_day_minutes // 60
                month_day_mins = month_day_minutes % 60
                month_night_hours = month_night_minutes // 60
                month_night_mins = month_night_minutes % 60
                month_total_amount = sum(r['subsidy_amount'] for r in month_rows)

                # 月ごとの補助基準額を計算
                month_subsidy_amount = (month_day_hours * 2500) + (month_night_hours * 3500)
                month_request_amount = min(month_subsidy_amount, month_total_amount)

                result["page2"][f"month{idx}"] = month
                result["page2"][f"table{idx}"] = {
                    "rows": month_rows,
                    "dayTotalTime": f"{month_day_hours}時間{month_day_mins:02d}分",
                    "nightTotalTime": f"{month_night_hours}時間{month_night_mins:02d}分" if month_night_hours > 0 else "",
                    "totalAmount": f"{month_total_amount:,}",
                    "dayHours": str(month_day_hours),
                    "nightHours": str(month_night_hours),
                    "subsidyAmount": f"{month_subsidy_amount:,}",
                    "requestAmount": f"{month_request_amount:,}",
                    "usageHours": str(month_day_hours + month_night_hours)
                }

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        return jsonify({"error": f"変換エラー: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Gunicorn経由で起動される場合はこのブロックは実行されない
    # 開発環境でのみ使用
    app.run(host='0.0.0.0', port=port, debug=False)
