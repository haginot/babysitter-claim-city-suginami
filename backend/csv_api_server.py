#!/usr/bin/env python3
"""
CSV Data API Server
請求書CSVデータの読み込み・保存を行うAPIサーバー
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import json
import os
import sys
from datetime import datetime

app = Flask(__name__)
CORS(app)  # CORSを有効化

# CSVファイルのパス
CSV_FILE_PATH = '/app/data/invoice-data.csv'

# CSVヘッダーの定義
CSV_HEADERS = [
    'ご利用日', '開始時刻', '終了時刻', 'シッター名', 'お子さま',
    '保育料 (非課税)', '保育料 (税込10%)', 'オプション料 (税込10%)',
    '交通費 (税込11%)', '特別費用 (税込10%)', 'キャンセル料 (不課税)',
    '割引額', 'お支払い額', '(一時預かりのみ) 助成対象金額'
]

# フィールドマッピング（フロントエンド用）
FIELD_MAPPING = {
    'ご利用日': '利用日',
    '開始時刻': '開始時刻',
    '終了時刻': '終了時刻',
    'シッター名': 'シッター名',
    'お子さま': 'お子さま',
    '保育料 (非課税)': '保育料_非課税',
    '保育料 (税込10%)': '保育料_税込10',
    'オプション料 (税込10%)': 'オプション料_税込10',
    '交通費 (税込11%)': '交通費_税込11',
    '特別費用 (税込10%)': '特別費用_税込10',
    'キャンセル料 (不課税)': 'キャンセル料_不課税',
    '割引額': '割引額',
    'お支払い額': 'お支払い額',
    '(一時預かりのみ) 助成対象金額': '助成対象金額'
}

# 逆マッピング（保存用）
REVERSE_FIELD_MAPPING = {v: k for k, v in FIELD_MAPPING.items()}

def get_csv_file_path():
    """CSVファイルの絶対パスを取得"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, CSV_FILE_PATH)

def validate_csv_data(data):
    """CSVデータの検証"""
    if not isinstance(data, list):
        return False, "データは配列である必要があります"
    
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            return False, f"行{i+1}は辞書である必要があります"
        
        # 必須フィールドの確認
        required_fields = ['利用日', 'シッター名', 'お子さま']
        for field in required_fields:
            if field not in row or not row[field]:
                return False, f"行{i+1}の{field}は必須項目です"
        
        # 日付フォーマットの確認
        if row.get('利用日'):
            try:
                datetime.strptime(row['利用日'], '%Y/%m/%d')
            except ValueError:
                return False, f"行{i+1}の利用日は YYYY/MM/DD 形式で入力してください"
        
        # 時刻フォーマットの確認
        for time_field in ['開始時刻', '終了時刻']:
            if row.get(time_field):
                try:
                    datetime.strptime(row[time_field], '%H:%M')
                except ValueError:
                    return False, f"行{i+1}の{time_field}は HH:MM 形式で入力してください"
    
    return True, "データは有効です"

@app.route('/api/csv/read', methods=['GET'])
def read_csv():
    """CSVファイルからデータを読み込む"""
    try:
        csv_path = get_csv_file_path()
        
        if not os.path.exists(csv_path):
            # CSVファイルが存在しない場合は空の配列を返す
            return jsonify({
                'success': True,
                'rows': [],
                'message': 'CSVファイルが見つかりません。新しいデータを作成してください。'
            })
        
        # CSVファイルを読み込み
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # データを辞書のリストに変換
        rows = []
        for _, row in df.iterrows():
            row_data = {}
            for csv_header, frontend_field in FIELD_MAPPING.items():
                value = row.get(csv_header, '')
                # NaNや空の値を空文字に変換
                if pd.isna(value) or value is None:
                    value = ''
                row_data[frontend_field] = str(value)
            rows.append(row_data)
        
        return jsonify({
            'success': True,
            'rows': rows,
            'message': f'{len(rows)}件のデータを読み込みました'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'データの読み込みでエラーが発生しました'
        }), 500

@app.route('/api/csv/save', methods=['POST'])
def save_csv():
    """CSVファイルにデータを保存する"""
    try:
        data = request.get_json()
        
        if not data or 'rows' not in data:
            return jsonify({
                'success': False,
                'error': 'リクエストデータが不正です'
            }), 400
        
        rows = data['rows']
        
        # データの検証
        is_valid, message = validate_csv_data(rows)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': message
            }), 400
        
        # DataFrameに変換
        df_data = []
        for row in rows:
            df_row = {}
            for frontend_field, csv_header in REVERSE_FIELD_MAPPING.items():
                value = row.get(frontend_field, '')
                df_row[csv_header] = value
            df_data.append(df_row)
        
        df = pd.DataFrame(df_data)
        
        # CSVファイルパスを取得
        csv_path = get_csv_file_path()
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        # バックアップを作成
        if os.path.exists(csv_path):
            backup_path = csv_path + '.backup.' + datetime.now().strftime('%Y%m%d_%H%M%S')
            import shutil
            shutil.copy2(csv_path, backup_path)
        
        # CSVファイルに保存
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        return jsonify({
            'success': True,
            'message': f'{len(rows)}件のデータを保存しました',
            'saved_count': len(rows)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'データの保存でエラーが発生しました'
        }), 500

@app.route('/api/csv/backup', methods=['GET'])
def list_backups():
    """バックアップファイルの一覧を取得"""
    try:
        csv_path = get_csv_file_path()
        csv_dir = os.path.dirname(csv_path)
        csv_filename = os.path.basename(csv_path)
        
        backups = []
        if os.path.exists(csv_dir):
            for file in os.listdir(csv_dir):
                if file.startswith(csv_filename + '.backup.'):
                    backup_path = os.path.join(csv_dir, file)
                    stat = os.stat(backup_path)
                    backups.append({
                        'filename': file,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                        'size': stat.st_size
                    })
        
        # 作成日時でソート
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'backups': backups
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/csv/validate', methods=['POST'])
def validate_data():
    """データの検証"""
    try:
        data = request.get_json()
        
        if not data or 'rows' not in data:
            return jsonify({
                'success': False,
                'error': 'リクエストデータが不正です'
            }), 400
        
        rows = data['rows']
        is_valid, message = validate_csv_data(rows)
        
        return jsonify({
            'success': True,
            'is_valid': is_valid,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'csv_path': get_csv_file_path(),
        'csv_exists': os.path.exists(get_csv_file_path())
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'エンドポイントが見つかりません'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'サーバー内部エラーが発生しました'
    }), 500

if __name__ == '__main__':
    # デバッグモードで起動
    app.run(host='0.0.0.0', port=5000, debug=True) 