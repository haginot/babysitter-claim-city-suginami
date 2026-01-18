from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import os
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)


def parse_kidsline_receipt(text):
    """
    キッズラインの領収書PDFからデータを抽出する
    1利用1PDF形式に対応
    """
    result = {
        'date': None,           # 利用日 (YYYY/MM/DD形式)
        'start_time': None,     # 開始時刻
        'end_time': None,       # 終了時刻
        'sitter_name': None,    # シッター名
        'child_name': None,     # お子様名
        'childcare_fee': 0,     # 保育料
        'option_fee': 0,        # オプション料金
        'transport_fee': 0,     # 交通費
        'total_amount': 0,      # お支払い額
        'total_duration': None, # 合計時間（例：8時間 0分）
    }
    
    # テキストを行ごとに分割
    lines = text.split('\n')
    full_text = ' '.join(lines)
    
    # 領収日から年を取得
    # 「領収日」と「:」の間にスペースがある場合に対応
    receipt_date_match = re.search(r'領収日\s*[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日', full_text)
    year = None
    if receipt_date_match:
        year = receipt_date_match.group(1)
    
    # ご利用日時を解析
    # パターン: 12月07日(日) 09:00～17:00　合計8時間 0分
    # 「ご利用日時」と「:」の間にスペースがある場合に対応
    datetime_match = re.search(
        r'ご利用日時\s*[：:]\s*(\d{1,2})月(\d{1,2})日[（(][日月火水木金土][）)]\s*(\d{1,2}:\d{2})[～〜\-](\d{1,2}:\d{2})\s*合計\s*(\d+時間\s*\d+分)',
        full_text
    )
    if datetime_match:
        month = datetime_match.group(1).zfill(2)
        day = datetime_match.group(2).zfill(2)
        if year:
            result['date'] = f"{year}/{month}/{day}"
        else:
            # 年が取れない場合は現在の年を使用
            result['date'] = f"{datetime.now().year}/{month}/{day}"
        result['start_time'] = datetime_match.group(3)
        result['end_time'] = datetime_match.group(4)
        result['total_duration'] = datetime_match.group(5).replace(' ', '')
    
    # ベビーシッター名
    # 「ベビーシッター名（フリガナ）」や「ベビーシッター要件」を除外し、
    # 「ベビーシッター : 名前」形式を抽出
    # 「ベビーシッター」の後に「名」「要件」が続かないものを探す
    sitter_match = re.search(r'ベビーシッター\s*[：:]\s*([^\n\r（(]+?)(?=\s*[\n\r]|お子様|$)', full_text)
    if sitter_match:
        sitter_name = sitter_match.group(1).strip()
        # 「名（フリガナ）」や「要件」で始まる場合は除外
        if not sitter_name.startswith('名') and not sitter_name.startswith('要件'):
            result['sitter_name'] = sitter_name
    
    # お子様名
    # 「お子様」と「:」の間にスペースがある場合に対応
    child_match = re.search(r'お子様\s*[：:]\s*([^\n\r（(]+)', full_text)
    if child_match:
        result['child_name'] = child_match.group(1).strip()
    
    # 金額を解析
    # 保育料（①保育料）
    childcare_match = re.search(r'[①]?\s*保育料[^¥￥]*[¥￥]([0-9,]+)', full_text)
    if childcare_match:
        result['childcare_fee'] = int(childcare_match.group(1).replace(',', ''))
    
    # オプション料金
    option_match = re.search(r'オプション料金?[^¥￥]*[¥￥]([0-9,]+)', full_text)
    if option_match:
        result['option_fee'] = int(option_match.group(1).replace(',', ''))
    
    # 交通費
    transport_match = re.search(r'交通費[^¥￥]*[¥￥]([0-9,]+)', full_text)
    if transport_match:
        result['transport_fee'] = int(transport_match.group(1).replace(',', ''))
    
    # お支払い額（総額）
    total_match = re.search(r'お客様のお支払い[^¥￥]*[¥￥]([0-9,]+)', full_text)
    if not total_match:
        # ヘッダーの金額も試す
        total_match = re.search(r'様\s*[¥￥]([0-9,]+)\s*上記の通り領収', full_text)
    if total_match:
        result['total_amount'] = int(total_match.group(1).replace(',', ''))
    
    return result


def is_kidsline_receipt(text):
    """
    テキストがキッズラインの領収書かどうかを判定する
    
    キッズライン特有の指標：
    - 「キッズライン」または「KIDSLINE」という文字列
    - 「領収書 兼 利用明細書」形式（キッズライン特有）
    - 「株式会社キッズライン」
    
    注意: 「東京都ベビーシッター利用支援事業」や「ベビーシッター要件証明書」は
    スマートシッター等の他サービスでも使われるため判定条件から除外
    """
    text_lower = text.lower()
    
    # キッズライン固有の指標（これらがあれば確実にキッズライン）
    kidsline_specific = [
        'キッズライン',
        'kidsline',
        '株式会社キッズライン'
    ]
    
    for indicator in kidsline_specific:
        if indicator.lower() in text_lower:
            return True
    
    # 「領収書 兼 利用明細書」はキッズライン特有の形式
    # ただし、他の事業者名（ポピンズシッターなど）が含まれていない場合のみ
    if '領収書 兼 利用明細書' in text or '領収書兼利用明細書' in text.replace(' ', ''):
        # 他の事業者名が含まれていないかチェック
        other_providers = ['ポピンズ', 'スマートシッター', 'poppins']
        has_other_provider = any(p.lower() in text_lower for p in other_providers)
        if not has_other_provider:
            return True
    
    return False

# 標準ヘッダー（キッズライン領収書と請求書形式で統一）
STANDARD_HEADER = [
    'ご利用日', '開始時刻', '終了時刻', 'シッター名', 'お子さま',
    '保育料(非課税)', '保育料(税込10%)', 'オプション料(税込10%)',
    '交通費(税込11%)', '特別費用(税込10%)', 'キャンセル料(不課税)',
    '割引額', 'お支払い額', '(一時預かりのみ)助成対象金額'
]

# ヘッダーマッピング（請求書形式のヘッダー名 → 標準インデックス）
HEADER_MAPPING = {
    'ご利用日': 0, 'ご利⽤⽇': 0, '利用日': 0, '利⽤⽇': 0,
    '開始時刻': 1, '開始': 1, '開始時間': 1,
    '終了時刻': 2, '終了': 2, '終了時間': 2,
    'シッター名': 3, 'シッター': 3, 'ベビーシッター': 3, '担当者': 3,
    'お子さま': 4, 'お子様': 4, '児童名': 4, '子供': 4,
    '保育料(非課税)': 5, '保育料（非課税）': 5, '保育料': 5,
    '保育料(税込10%)': 6, '保育料（税込10%）': 6,
    'オプション料(税込10%)': 7, 'オプション料（税込10%）': 7, 'オプション料': 7, 'オプション': 7,
    '交通費(税込11%)': 8, '交通費（税込11%）': 8, '交通費': 8,
    '特別費用(税込10%)': 9, '特別費用（税込10%）': 9, '特別費用': 9,
    'キャンセル料(不課税)': 10, 'キャンセル料（不課税）': 10, 'キャンセル料': 10,
    '割引額': 11, '割引': 11,
    'お支払い額': 12, '支払い額': 12, '合計金額': 12, '請求額': 12,
    '(一時預かりのみ)助成対象金額': 13, '助成対象金額': 13, '助成対象': 13
}


def normalize_header(header_cell):
    """ヘッダーセルを正規化"""
    if not header_cell:
        return ''
    # スペースと改行を削除
    normalized = str(header_cell).replace(' ', '').replace('　', '').replace('\n', '').strip()
    return normalized


def map_row_to_standard(row, header_indices):
    """
    行データを標準形式にマッピング
    header_indices: {標準インデックス: 元のインデックス}
    """
    standard_row = [''] * len(STANDARD_HEADER)
    for std_idx, orig_idx in header_indices.items():
        if orig_idx < len(row):
            standard_row[std_idx] = row[orig_idx] or ''
    return standard_row


def parse_invoice_table(pdf_file):
    """
    請求書形式のPDFからテーブルを抽出する
    返り値: {"success": bool, "table": [...], "error": str}
    """
    try:
        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) == 0:
                return {"success": False, "error": "PDFにページがありません"}

            # 1ページ目を取得
            first_page = pdf.pages[0]

            # テーブルを抽出
            tables = first_page.extract_tables()

            if not tables:
                return {"success": False, "error": "テーブルが見つかりませんでした"}

            # すべてのテーブルから「ご利用日」セルを探索
            target_table = None
            target_row_idx = None
            target_col_idx = None
            min_cell_length = float('inf')

            for table in tables:
                if not table or len(table) == 0:
                    continue

                for row_idx, row in enumerate(table):
                    if not row:
                        continue

                    for col_idx, cell in enumerate(row):
                        if cell:
                            cell_str = str(cell).strip()
                            normalized_cell = cell_str.replace(' ', '').replace('　', '')

                            if ('ご利用日' in normalized_cell or
                                'ご利⽤⽇' in normalized_cell or
                                '利用日' in normalized_cell or
                                '利⽤⽇' in normalized_cell):
                                cell_length = len(normalized_cell)
                                if cell_length < min_cell_length:
                                    target_table = table
                                    target_row_idx = row_idx
                                    target_col_idx = col_idx
                                    min_cell_length = cell_length

            if not target_table:
                return {"success": False, "error": "「ご利用日」を含むテーブルが見つかりませんでした"}

            # テーブルをトリミング
            trimmed_table = []
            for row in target_table[target_row_idx:]:
                if row and len(row) > target_col_idx:
                    trimmed_row = row[target_col_idx:]
                    trimmed_table.append(trimmed_row)

            # 空行と「合計」行を削除
            filtered_table = []
            for row in trimmed_table:
                if not row or not any(cell for cell in row):
                    continue
                row_text = ''.join([str(cell).replace(' ', '').replace('　', '') for cell in row if cell])
                if '合計' in row_text or '⼩計' in row_text:
                    continue
                filtered_table.append(row)

            if not filtered_table:
                return {"success": False, "error": "テーブルのトリミングに失敗しました"}

            # Noneを空文字列に変換し、改行を削除
            cleaned_table = []
            for row in filtered_table:
                if row:
                    cleaned_row = []
                    for cell in row:
                        if cell:
                            cell_str = str(cell).replace('\n', ' ').replace('\r', ' ').strip()
                            cell_str = ' '.join(cell_str.split())
                            cleaned_row.append(cell_str)
                        else:
                            cleaned_row.append("")
                    cleaned_table.append(cleaned_row)
                else:
                    cleaned_table.append([])

            if not cleaned_table:
                return {"success": False, "error": "テーブルデータが空です"}

            # ヘッダー行を解析して標準形式にマッピング
            original_header = cleaned_table[0]
            header_indices = {}  # {標準インデックス: 元のインデックス}
            
            for orig_idx, cell in enumerate(original_header):
                normalized = normalize_header(cell)
                # 完全一致を優先
                if normalized in HEADER_MAPPING:
                    std_idx = HEADER_MAPPING[normalized]
                    if std_idx not in header_indices:
                        header_indices[std_idx] = orig_idx
                else:
                    # 部分一致を試みる
                    for key, std_idx in HEADER_MAPPING.items():
                        if key in normalized or normalized in key:
                            if std_idx not in header_indices:
                                header_indices[std_idx] = orig_idx
                                break

            # 標準形式のテーブルを作成
            standardized_table = [STANDARD_HEADER.copy()]
            for row in cleaned_table[1:]:  # ヘッダー行をスキップ
                standardized_row = map_row_to_standard(row, header_indices)
                standardized_table.append(standardized_row)

            return {
                "success": True,
                "table": standardized_table,
                "rows": len(standardized_table),
                "columns": len(STANDARD_HEADER),
                "original_columns": len(original_header),
                "mapped_columns": len(header_indices)
            }

    except Exception as e:
        return {"success": False, "error": f"テーブル抽出エラー: {str(e)}"}


@app.route('/api/extract-auto', methods=['POST'])
def extract_auto():
    """
    単一PDFを自動判定して抽出する
    キッズライン領収書か請求書形式かを自動判別
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "ファイルがアップロードされていません"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "ファイル名が空です"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "PDFファイルのみアップロード可能です"}), 400
        
        pdf_bytes = file.read()
        pdf_file = io.BytesIO(pdf_bytes)
        
        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) == 0:
                return jsonify({"error": "PDFにページがありません"}), 400
            
            # 全ページのテキストを結合
            all_text = ''
            for page in pdf.pages:
                page_text = page.extract_text() or ''
                all_text += page_text + '\n'
        
        # フォーマットを判定
        is_kidsline = is_kidsline_receipt(all_text)
        
        # ファイルポインタをリセット
        pdf_file.seek(0)
        
        if is_kidsline:
            # キッズライン領収書として処理
            data = parse_kidsline_receipt(all_text)
            
            if not data['date'] or not data['start_time']:
                return jsonify({
                    "success": False,
                    "error": "利用日時が抽出できませんでした",
                    "format": "kidsline",
                    "filename": file.filename
                }), 400
            
            # テーブル形式に変換
            row = [
                data['date'],
                data['start_time'],
                data['end_time'],
                data['sitter_name'] or '',
                data['child_name'] or '',
                str(data['childcare_fee']),
                '0',
                str(data['option_fee']),
                str(data['transport_fee']),
                '0',
                '0',
                '0',
                str(data['total_amount']),
                str(data['childcare_fee'])
            ]
            
            return jsonify({
                "success": True,
                "format": "kidsline",
                "filename": file.filename,
                "table": [STANDARD_HEADER.copy(), row],
                "rows": 2,
                "columns": len(STANDARD_HEADER),
                "child_name": data['child_name'],
                "sitter_name": data['sitter_name']
            })
        
        else:
            # 請求書形式として処理
            result = parse_invoice_table(pdf_file)
            
            if not result['success']:
                return jsonify({
                    "success": False,
                    "error": result['error'],
                    "format": "invoice",
                    "filename": file.filename
                }), 400
            
            return jsonify({
                "success": True,
                "format": "invoice",
                "filename": file.filename,
                "table": result['table'],
                "rows": result['rows'],
                "columns": result['columns']
            })
    
    except Exception as e:
        return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/api/extract-kidsline', methods=['POST'])
def extract_kidsline():
    """
    キッズラインの領収書PDFからデータを抽出する
    複数のPDFをアップロードして連結可能
    """
    try:
        if 'files' not in request.files and 'file' not in request.files:
            return jsonify({"error": "ファイルがアップロードされていません"}), 400
        
        # 単一ファイルまたは複数ファイルに対応
        if 'files' in request.files:
            files = request.files.getlist('files')
        else:
            files = [request.files['file']]
        
        if len(files) == 0:
            return jsonify({"error": "ファイルがアップロードされていません"}), 400
        
        extracted_rows = []
        child_name = None
        applicant_name = None
        
        for file in files:
            if file.filename == '':
                continue
            
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"error": f"{file.filename}: PDFファイルのみアップロード可能です"}), 400
            
            pdf_bytes = file.read()
            pdf_file = io.BytesIO(pdf_bytes)
            
            with pdfplumber.open(pdf_file) as pdf:
                if len(pdf.pages) == 0:
                    continue
                
                # 全ページのテキストを結合
                all_text = ''
                for page in pdf.pages:
                    page_text = page.extract_text() or ''
                    all_text += page_text + '\n'
                
                # キッズライン領収書かどうかをチェック
                if not is_kidsline_receipt(all_text):
                    return jsonify({
                        "error": f"{file.filename}: キッズラインの領収書形式ではありません",
                        "hint": "請求書形式のPDFは「テーブル抽出」機能をお使いください"
                    }), 400
                
                # データを抽出
                data = parse_kidsline_receipt(all_text)
                
                if not data['date'] or not data['start_time']:
                    return jsonify({
                        "error": f"{file.filename}: 利用日時が抽出できませんでした"
                    }), 400
                
                # 子供の名前と保護者名を保存（最初に見つかったもの）
                if child_name is None and data['child_name']:
                    child_name = data['child_name']
                
                # テーブル形式に変換
                row = [
                    data['date'],                           # ご利用日
                    data['start_time'],                     # 開始時刻
                    data['end_time'],                       # 終了時刻
                    data['sitter_name'] or '',              # シッター名
                    data['child_name'] or '',               # お子さま
                    str(data['childcare_fee']),             # 保育料(非課税) - 助成対象
                    '0',                                    # 保育料(税込10%)
                    str(data['option_fee']),                # オプション料(税込10%)
                    str(data['transport_fee']),             # 交通費(税込11%)
                    '0',                                    # 特別費用(税込10%)
                    '0',                                    # キャンセル料(不課税)
                    '0',                                    # 割引額
                    str(data['total_amount']),              # お支払い額
                    str(data['childcare_fee'])              # 助成対象金額（保育料）
                ]
                extracted_rows.append(row)
        
        if len(extracted_rows) == 0:
            return jsonify({"error": "有効なデータが抽出できませんでした"}), 400
        
        # 日付順にソート
        extracted_rows.sort(key=lambda x: x[0])
        
        table = [STANDARD_HEADER.copy()] + extracted_rows
        
        return jsonify({
            "success": True,
            "table": table,
            "rows": len(table),
            "columns": len(STANDARD_HEADER),
            "format": "kidsline",
            "child_name": child_name
        })
    
    except Exception as e:
        return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500


@app.route('/api/detect-pdf-format', methods=['POST'])
def detect_pdf_format():
    """
    PDFのフォーマットを自動検出する
    - kidsline: キッズライン領収書形式（1利用1PDF）
    - invoice: 請求書形式（テーブル形式、複数利用）
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "ファイルがアップロードされていません"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "ファイル名が空です"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "PDFファイルのみアップロード可能です"}), 400
        
        pdf_bytes = file.read()
        pdf_file = io.BytesIO(pdf_bytes)
        
        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) == 0:
                return jsonify({"error": "PDFにページがありません"}), 400
            
            # 最初のページのテキストを取得
            first_page = pdf.pages[0]
            text = first_page.extract_text() or ''
            
            # フォーマットを判定
            if is_kidsline_receipt(text):
                return jsonify({
                    "success": True,
                    "format": "kidsline",
                    "description": "キッズライン領収書形式"
                })
            else:
                return jsonify({
                    "success": True,
                    "format": "invoice",
                    "description": "請求書形式（テーブル）"
                })
    
    except Exception as e:
        return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500


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
