# from flask import Flask リモートホスト用※from flaskr import appは消す
from flaskr import app
from flask import render_template, request, redirect, url_for, json #HTMLのデータを読み込んでPythonのデータに埋め込んで表示させる ※jinja2を使ってる
import gspread  #gspreadモジュールをインポート
import os
from google.oauth2.service_account import Credentials
from datetime import date, datetime
from flaskr.master_login import get_office_name
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user

# app = Flask(__name__)リモートホスト用


#開発モード用
# json_file_path = "spread-sheet-test.json" 
#WEBアプリ用
json_file_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

scopes = ["https://www.googleapis.com/auth/spreadsheets"] #スコープ：どの範囲でまでその権限・影響を及ばせるか 今回のパターンで行くとスプレッドシートの読み書きが行える

# from_service_account_file関数に引数json_file_path, scopes=scopesを渡すことでクラスメソッドとしてCredentialsクラスに値を渡しインスタンス変数を設定。
# グーグルアカウントの認証管理をするクラスメソッド
credentials = Credentials.from_service_account_file(
    json_file_path, scopes=scopes)

# authorizeはgspreadモジュールの関数。「この認証情報を使って、スプレッドシートを操作する許可をください！」というリクエストを送る
# 認証されたらClientを返し、gspread.Clientオブジェクトとしてスプレッドシートの操作オブジェクトとなる
gc = gspread.authorize(credentials)

spreadsheet_id = "1kSXfl_g3WwopEyGIIvswYzNFwotVqh_g1DPNI31gb_w"
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1kSXfl_g3WwopEyGIIvswYzNFwotVqh_g1DPNI31gb_w/edit?gid=0#gid=0"
spreadsheet_url_2 = "https://docs.google.com/spreadsheets/d/1kSXfl_g3WwopEyGIIvswYzNFwotVqh_g1DPNI31gb_w/edit?gid=1221591128#gid=1221591128"
sh = gc.open_by_key(spreadsheet_id)
ws = sh.get_worksheet(0)
ws_2 = sh.get_worksheet(1)

#   #クラスメソッドで本日の日付と曜日を取得
today =date.today()
week = ["（月）", "（火）", "（水）", "（木）", "（金）", "（土）", "（日）"]
today_str = today.isoformat()#isoformatメソッドで今日の日付を文字列にする
today_week = week[today.weekday()] #weekdayメソッドは取得した日付の曜日を数字として表す
today_full = f"{today_str} {today_week}"
    
@app.route("/spread", methods=["GET", "POST"]) 
#POST:入力データを送る、GET:ページを開く POSTは送る側・貰う側両方設定必要。（GETは貰う側だけでOK)
@login_required
def spread():
    if request.method == "POST":
        # フォームのデータを取得
        report_data = request.form["report"]
        revenue_data = request.form["revenue"]
        budget_data = request.form["budget"]
        mile_data = request.form["mile"]  
        
        #事業所名をDBから取得
        office_name = get_office_name(current_user.id)
        
        #曜日ごとの色の設定
        weekday_colors =  {
            0: {"red": 0.9, "green": 0.95, "blue": 1.0},  # 月曜: 超薄い青
            1: {"red": 1.0, "green": 0.95, "blue": 0.95},  # 火曜: 超薄い赤
            2: {"red": 1.0, "green": 1.0, "blue": 0.85},  # 水曜: 超薄い黄色
            3: {"red": 0.95, "green": 1.0, "blue": 0.95},  # 木曜: 超薄い緑
            4: {"red": 1.0, "green": 0.95, "blue": 0.85},  # 金曜: 超薄いオレンジ
            5: {"red": 0.97, "green": 0.92, "blue": 1.0},  # 土曜: 超薄い紫
            6: {"red": 1.0, "green": 1.0, "blue": 1.0}   # 日曜: 超薄い水色（白に近い）
        }

        
        
        # 新しい業務報告データ（3行目に挿入する）
        #各列にフォームから取得して下記リストのデータを入れる
        new_data = [
            "",
            today_full,   # B列: 日付
            "VP" + office_name,  # C列: 事業所名
            revenue_data + "万円",  # D列: 売上予測
            budget_data + "万円",   # E列: 予算差
            mile_data,    # F列: マイルストーンチェック
            report_data   # G列: 備考
        ]
        
         # 3行目に新しいデータを挿入し、既存データを1行ずつ下へずらす （基本）ws.insert_row(データのリスト, 挿入する行の位置)
        ws.insert_row(new_data, index=3)

         # 予算差がマイナスの場合、E列を赤字にする 
        if "-" in budget_data:
            ws.format("E3", {
                "textFormat": {"foregroundColor": {"red": 1, "green": 0, "blue": 0}, "bold": True, "fontSize": 15}
            })
        else:
            ws.format("E3", {
                "textFormat": {"foregroundColor": {"red": 0, "green": 0, "blue": 0}, "bold": True, "fontSize": 15}
            })
       
        #曜日ごとにセルの色が変わる
        ws.format("B3:G3", {
            "backgroundColor": weekday_colors[today.weekday()]})

        # マイルストーン振り返り期間中はB列の日付に色をつける
        today_day = today.day #today.dayのdayはプロパティ（値だけを取得したい）ので（）はいらない
        if today_day in [3, 4, 5, 19, 20, 21]: #if today_day == 3 or 4 or 5 or 19 or 20 or 21:この書き方は×or以降”数値”として判断されるから０以外全部tureになる
            ws.format("B3", {
                "textFormat": {"foregroundColor": {"red": 0, "green": 0, "blue": 2}, "bold": True, "fontSize": 12}
            })
        else:
            ws.format("B3", {
                "textFormat": {"foregroundColor": {"red": 0, "green": 0, "blue": 0}, "bold": False, "fontSize": 10}
            })
        
            
        #マイストーンチェックをプルダウン化にする
        if mile_data == "option2":
            ws.update_acell(f"F3","〇")
        else:
            ws.update_acell(f"F3","")
        
         # 送信後スプレッドシートへ飛ぶ HTMLファイルに飛ばしたいときはrender_template、URLに飛ばしたかったらredirect
        return redirect(spreadsheet_url)

    return render_template("report.html") #GETに対応。spread関数を実行するときにreport.htmlを開く
    
@app.route("/spread_link")
def spread_link():
    return redirect(spreadsheet_url)


today_2 = datetime.today().strftime("%Y-%m-%d")

#業務報告をする、見る画面
@app.route("/title", methods=["POST", "GET"])
@login_required
def title():
    # 初期化
    abi = None  
    coment = None  
    office_name = get_office_name(current_user.id)
    
    special_days = [3, 4, 5, 19, 20, 21, 22, 28]
    message = "マイルストーン振り返りの期間です" if today.day in special_days else ""
    
    today_with_week = f"{today_str} {today_week}"

    # 今日の日付を取得
    today_2 = datetime.today().strftime('%Y-%m-%d')

    # 期限とタスクのリストを取得
    data = ws_2.get_values("B2:C")  

    # 今日のタスクを取得
    today_tasks = [task_name for deadline, task_name in data if deadline == today_2]

    # **GETでもPOSTでも常に今日のタスクを表示**
    abi = today_tasks if today_tasks else None
    coment = None if today_tasks else "本日のタスクはありません"

    if request.method == "POST":
        # フォームからデータ取得
        deadline = request.form["deadline"]
        task_name = request.form["task"]  
        new_task = [deadline, task_name]
        ws_2.append_row(new_task)  

        # POST時も再度タスクリストを取得して更新
        data = ws_2.get_values("B2:C")  
        today_tasks = [task_name for deadline, task_name in data if deadline == today_2]
        abi = today_tasks if today_tasks else None
        coment = None if today_tasks else "本日のタスクはありません"

    return render_template(
        "title.html",
        message=message,
        today=today_with_week,
        office_name=office_name,
        abi=abi,
        coment=coment
    )
# if __name__ == "__main__" :
#     app.run(host="0.0.0.0", port=8090, debug=True)　リモートホスト用


