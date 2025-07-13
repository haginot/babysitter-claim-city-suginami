#!/usr/bin/env python3
"""
Invoice to Form Data Converter
請求書CSVファイルを杉並区ベビーシッター助成申請書フォーマット(JSON)に変換するプログラム
"""

import pandas as pd
import json
import argparse
import os
from datetime import datetime, timedelta
from collections import defaultdict
import re

def parse_time(time_str):
    """時刻文字列をdatetimeオブジェクトに変換"""
    if not time_str or pd.isna(time_str):
        return None
    try:
        return datetime.strptime(time_str.strip(), "%H:%M")
    except ValueError:
        return None

def calculate_duration(start_time, end_time):
    """開始時刻と終了時刻から利用時間を計算"""
    if not start_time or not end_time:
        return 0, 0  # 昼間時間, 夜間時間（分）
    
    current_time = start_time
    day_minutes = 0
    night_minutes = 0
    
    while current_time < end_time:
        next_minute = current_time + timedelta(minutes=1)
        if next_minute > end_time:
            next_minute = end_time
        
        # 22:00以降は夜間料金
        if current_time.hour >= 22 or current_time.hour < 6:
            night_minutes += 1
        else:
            day_minutes += 1
        
        current_time = next_minute
    
    return day_minutes, night_minutes

def minutes_to_duration_str(minutes):
    """分を「X時間Y分」形式に変換"""
    if minutes == 0:
        return ""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}時間{mins:02d}分"

def format_time_range(start_time, end_time):
    """時間範囲を「HH:MM ～ HH:MM」形式に変換"""
    if not start_time or not end_time:
        return ""
    return f"{start_time.strftime('%H:%M')} ～ {end_time.strftime('%H:%M')}"

def get_day_night_time_ranges(start_time, end_time):
    """昼間と夜間の時間範囲を分割"""
    if not start_time or not end_time:
        return "", ""
    
    # 22:00を境界として使用
    night_start = start_time.replace(hour=22, minute=0, second=0, microsecond=0)
    morning_end = start_time.replace(hour=6, minute=0, second=0, microsecond=0)
    
    day_range = ""
    night_range = ""
    
    # 昼間の時間範囲を計算
    day_start = None
    day_end = None
    
    if start_time.hour < 22 and start_time.hour >= 6:
        day_start = start_time
        if end_time.hour < 22 and end_time.hour >= 6:
            day_end = end_time
        else:
            day_end = night_start
    
    if day_start and day_end and day_start < day_end:
        day_range = format_time_range(day_start, day_end)
    
    # 夜間の時間範囲を計算
    night_start_time = None
    night_end_time = None
    
    if start_time.hour >= 22 or start_time.hour < 6:
        night_start_time = start_time
        night_end_time = end_time
    elif end_time.hour >= 22 or end_time.hour < 6:
        night_start_time = night_start
        night_end_time = end_time
    
    if night_start_time and night_end_time and night_start_time < night_end_time:
        night_range = format_time_range(night_start_time, night_end_time)
    
    return day_range, night_range

def extract_child_name(child_field):
    """子供の名前フィールドから名前を抽出"""
    if not child_field or pd.isna(child_field):
        return "杉並 花子"  # デフォルト値
    
    # 「杉並 すけ様」から「杉並 すけ」を抽出
    match = re.match(r'^([^（]+)', str(child_field).strip())
    if match:
        name = match.group(1).replace('様', '').strip()
        return name if name else "杉並 花子"
    
    return "杉並 花子"

def extract_applicant_name(child_name):
    """子供の名前から申請者名を推定"""
    if "杉並" in child_name:
        return "杉並 太郎"
    return "杉並 太郎"  # デフォルト

def convert_invoice_to_form(csv_file, output_file=None):
    """
    Invoice CSVファイルをform-data.jsonに変換
    
    Args:
        csv_file (str): 入力CSVファイルのパス
        output_file (str): 出力JSONファイルのパス（省略時は自動生成）
    
    Returns:
        str: 出力ファイルのパス
    """
    
    print(f"CSVファイル '{csv_file}' を読み込み中...")
    
    # CSVファイルを読み込み
    try:
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
    except UnicodeDecodeError:
        df = pd.read_csv(csv_file, encoding='shift_jis')
    
    print(f"読み込み完了: {len(df)}行のデータ")
    print("列名:", df.columns.tolist())
    
    # データを月別に整理
    monthly_data = defaultdict(list)
    
    for _, row in df.iterrows():
        try:
            # 日付をパース
            date_str = str(row['ご利用日'])
            date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            
            # 時刻をパース
            start_time = parse_time(str(row['開始時刻']))
            end_time = parse_time(str(row['終了時刻']))
            
            if not start_time or not end_time:
                print(f"時刻データが無効: {row['ご利用日']}")
                continue
            
            # 時間を計算
            day_minutes, night_minutes = calculate_duration(start_time, end_time)
            day_range, night_range = get_day_night_time_ranges(start_time, end_time)
            
            # 金額を取得
            amount = int(row['お支払い額']) if pd.notna(row['お支払い額']) else 0
            subsidy_amount = int(row['(一時預かりのみ) 助成対象金額']) if pd.notna(row['(一時預かりのみ) 助成対象金額']) else amount
            
            # 子供の名前を取得
            child_name = extract_child_name(row['お子さま'])
            
            # 月別データに追加
            month_key = date_obj.month
            monthly_data[month_key].append({
                'date': str(date_obj.day),
                'dayTime': day_range,
                'dayDuration': minutes_to_duration_str(day_minutes),
                'nightTime': night_range,
                'nightDuration': minutes_to_duration_str(night_minutes),
                'amount': f"{amount:,}",
                'subsidy_amount': subsidy_amount,
                'day_minutes': day_minutes,
                'night_minutes': night_minutes
            })
            
        except Exception as e:
            print(f"行の処理でエラー: {e}")
            print(f"問題の行: {row['ご利用日']}")
            continue
    
    # JSONデータを構築
    if not monthly_data:
        print("処理できるデータがありません")
        return None
    
    # 最初の月をpage1として使用
    first_month = min(monthly_data.keys())
    first_month_data = monthly_data[first_month]
    
    # 子供の名前と申請者名を取得
    child_name = extract_child_name(df.iloc[0]['お子さま'] if not df.empty else "")
    applicant_name = extract_applicant_name(child_name)
    
    # page1データを作成
    page1_total_day_minutes = sum(item['day_minutes'] for item in first_month_data)
    page1_total_night_minutes = sum(item['night_minutes'] for item in first_month_data)
    page1_total_amount = sum(int(item['amount'].replace(',', '')) for item in first_month_data)
    page1_total_subsidy = sum(item['subsidy_amount'] for item in first_month_data)
    
    form_data = {
        "year": str(datetime.now().year - 2018),  # 令和年を計算
        "applicantName": applicant_name,
        "childName": child_name,
        "month": str(first_month),
        "page1": {
            "rows": first_month_data,
            "dayTotalTime": minutes_to_duration_str(page1_total_day_minutes),
            "nightTotalTime": minutes_to_duration_str(page1_total_night_minutes),
            "totalAmount": f"{page1_total_amount:,}",
            "dayHours": str(page1_total_day_minutes // 60),
            "nightHours": str(page1_total_night_minutes // 60),
            "subsidyAmount": f"{page1_total_subsidy:,}",
            "requestAmount": f"{page1_total_amount:,}",
            "usageHours": str((page1_total_day_minutes + page1_total_night_minutes) // 60)
        }
    }
    
    # 複数月のデータがある場合はpage2を作成
    if len(monthly_data) > 1:
        remaining_months = [month for month in sorted(monthly_data.keys()) if month != first_month]
        
        page2_data = {
            "grandTotal": {
                "totalDayHours": "0",
                "totalNightHours": "0",
                "totalSubsidyAmount": "0",
                "totalRequestAmount": "0",
                "totalUsageHours": "0"
            }
        }
        
        # 最初の追加月をtable1として設定
        if remaining_months:
            month1 = remaining_months[0]
            month1_data = monthly_data[month1]
            
            month1_day_minutes = sum(item['day_minutes'] for item in month1_data)
            month1_night_minutes = sum(item['night_minutes'] for item in month1_data)
            month1_amount = sum(int(item['amount'].replace(',', '')) for item in month1_data)
            month1_subsidy = sum(item['subsidy_amount'] for item in month1_data)
            
            page2_data["month1"] = str(month1)
            page2_data["table1"] = {
                "rows": month1_data,
                "dayTotalTime": minutes_to_duration_str(month1_day_minutes),
                "nightTotalTime": minutes_to_duration_str(month1_night_minutes),
                "totalAmount": f"{month1_amount:,}",
                "dayHours": str(month1_day_minutes // 60),
                "nightHours": str(month1_night_minutes // 60),
                "subsidyAmount": f"{month1_subsidy:,}",
                "requestAmount": f"{month1_amount:,}",
                "usageHours": str((month1_day_minutes + month1_night_minutes) // 60)
            }
        
        # 2番目の追加月をtable2として設定
        if len(remaining_months) > 1:
            month2 = remaining_months[1]
            month2_data = monthly_data[month2]
            
            month2_day_minutes = sum(item['day_minutes'] for item in month2_data)
            month2_night_minutes = sum(item['night_minutes'] for item in month2_data)
            month2_amount = sum(int(item['amount'].replace(',', '')) for item in month2_data)
            month2_subsidy = sum(item['subsidy_amount'] for item in month2_data)
            
            page2_data["month2"] = str(month2)
            page2_data["table2"] = {
                "rows": month2_data,
                "dayTotalTime": minutes_to_duration_str(month2_day_minutes),
                "nightTotalTime": minutes_to_duration_str(month2_night_minutes),
                "totalAmount": f"{month2_amount:,}",
                "dayHours": str(month2_day_minutes // 60),
                "nightHours": str(month2_night_minutes // 60),
                "subsidyAmount": f"{month2_subsidy:,}",
                "requestAmount": f"{month2_amount:,}",
                "usageHours": str((month2_day_minutes + month2_night_minutes) // 60)
            }
        
        # 総合計を計算
        all_data = []
        for month_data in monthly_data.values():
            all_data.extend(month_data)
        
        total_day_minutes = sum(item['day_minutes'] for item in all_data)
        total_night_minutes = sum(item['night_minutes'] for item in all_data)
        total_amount = sum(int(item['amount'].replace(',', '')) for item in all_data)
        total_subsidy = sum(item['subsidy_amount'] for item in all_data)
        
        page2_data["grandTotal"] = {
            "totalDayHours": str(total_day_minutes // 60),
            "totalNightHours": str(total_night_minutes // 60),
            "totalSubsidyAmount": f"{total_subsidy:,}",
            "totalRequestAmount": f"{total_amount:,}",
            "totalUsageHours": str((total_day_minutes + total_night_minutes) // 60)
        }
        
        form_data["page2"] = page2_data
    
    # 出力ファイル名を決定
    if output_file is None:
        base_name = os.path.splitext(os.path.basename(csv_file))[0]
        output_file = f"{base_name}_converted.json"
    
    # JSONファイルに保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(form_data, f, ensure_ascii=False, indent=2)
    
    print(f"変換完了: {output_file}")
    print(f"処理した月数: {len(monthly_data)}")
    print(f"総データ行数: {sum(len(data) for data in monthly_data.values())}")
    
    return output_file

def main():
    parser = argparse.ArgumentParser(description='請求書CSVファイルを申請書フォーマットJSONに変換')
    parser.add_argument('csv_file', help='入力CSVファイルのパス')
    parser.add_argument('-o', '--output', help='出力JSONファイルのパス（省略時は自動生成）')
    
    args = parser.parse_args()
    
    # ファイルの存在確認
    if not os.path.exists(args.csv_file):
        print(f"エラー: CSVファイルが見つかりません: {args.csv_file}")
        return
    
    # 変換実行
    try:
        output_file = convert_invoice_to_form(args.csv_file, args.output)
        if output_file:
            print(f"\n変換が完了しました: {output_file}")
        else:
            print("変換に失敗しました")
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main() 