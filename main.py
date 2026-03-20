import time
import scratchattach as scratch3
from datetime import datetime, timedelta, timezone

# --- 設定項目 ---
PROJECT_ID = "1287281407"
JST = timezone(timedelta(hours=+9), 'JST')
IGNORE_USERS = ["Unknown User"]

def get_author_name(comment):
    try:
        author = comment.author() if callable(comment.author) else comment.author
        return str(author)
    except Exception:
        return "Unknown User"

def parse_scratch_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)

def get_last_monday():
    # 今のJST時刻を取得
    now = datetime.now(JST)
    # 今週の月曜日 00:00:00 を計算
    # weekday()は月曜が0, 日曜が6
    last_monday = now - timedelta(days=now.weekday())
    last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    # 比較のためにUTCに変換
    return last_monday.astimezone(timezone.utc)

def run_ranking():
    try:
        now_jst = datetime.now(JST)
        # 💡 集計開始地点を「今週の月曜0時」に設定
        start_time_utc = get_last_monday()
        start_time_jst = start_time_utc.astimezone(JST)

        print(f"🚀 週間集計開始 (対象: {start_time_jst.strftime('%m/%d %H:%M')} 〜 現在)")
        
        project = scratch3.get_project(PROJECT_ID)
        project.update() # 最新の状態に更新
        user_stats = {}

        # 週間だとコメント数が多いので、少し多めに遡る(5000件程度)
        for offset in range(0, 5000, 40): 
            try:
                comments = project.comments(limit=40, offset=offset)
            except Exception as e:
                print(f"⚠ 取得失敗: {e}")
                time.sleep(5)
                continue

            if not comments: break
            
            stop_signal = False
            for c in comments:
                dt = parse_scratch_date(c.datetime_created)
                
                # 💡 月曜0時より前のデータに到達したら停止
                if dt < start_time_utc:
                    print(f"⏳ 月曜日の境界線に到達。終了します。")
                    stop_signal = True
                    break
                
                user = get_author_name(c)
                if user not in IGNORE_USERS:
                    if user not in user_stats: user_stats[user] = {"p": 0, "r": 0}
                    user_stats[user]["p"] += 1
                
                try:
                    replies = c.replies()
                    for r in replies:
                        r_dt = parse_scratch_date(r.datetime_created)
                        if r_dt >= start_time_utc:
                            r_user = get_author_name(r)
                            if r_user not in IGNORE_USERS:
                                if r_user not in user_stats: user_stats[r_user] = {"p": 0, "r": 0}
                                user_stats[r_user]["r"] += 1
                except: pass
            
            if stop_signal: break
            time.sleep(0.2)

        sorted_users = sorted(user_stats.items(), key=lambda x: (x[1]["p"] + x[1]["r"]), reverse=True)

        # --- HTML作成 ---
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Scratch Weekly Ranking</title>
            <style>
                body {{ font-family: sans-serif; background: #fdf6e3; padding: 10px; }}
                .container {{ background: white; padding: 20px; border-radius: 15px; max-width: 700px; margin: auto; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
                h1 {{ color: #2ecc71; text-align: center; font-size: 1.4em; }}
                .info {{ text-align: center; color: #666; font-size: 0.9em; margin-bottom: 20px; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                #search {{ width: 100%; padding: 12px; margin-bottom: 20px; border: 2px solid #ddd; border-radius: 8px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ padding: 12px 8px; border-bottom: 1px solid #eee; text-align: left; }}
                th {{ background: #2ecc71; color: white; }}
                .total-num {{ font-weight: bold; color: #27ae60; font-size: 1.2em; }}
                .rank-1 {{ background: #fff4d1; border: 2px solid #f1c40f; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🗓️ 今週の活動ランキング</h1>
                <div class="info">
                    集計期間: {start_time_jst.strftime('%m/%d')} 〜 現在<br>
                    最終更新: {now_jst.strftime('%H:%M')} / 参加者: {len(sorted_users)}人
                </div>
                <input type="text" id="search" placeholder="自分の名前を検索..." onkeyup="filterTable()">
                <table id="rankingTable">
                    <thead><tr><th>順</th><th>ユーザー名</th><th>合計活動数</th></tr></thead>
                    <tbody>
        """
        for i, (user, stat) in enumerate(sorted_users):
            total = stat["p"] + stat["r"]
            row_class = 'class="rank-1"' if i == 0 else ""
            html_content += f"""
                        <tr {row_class}>
                            <td>{i+1}</td>
                            <td><strong>{user}</strong></td>
                            <td><span class="total-num">{total}</span> <span style="font-size:0.8em;color:#999;"> (コメ{stat['p']} / 返{stat['r']})</span></td>
                        </tr>"""
        html_content += """
                    </tbody>
                </table>
            </div>
            <script>
            function filterTable() {
                let filter = document.getElementById("search").value.toLowerCase();
                let tr = document.getElementById("rankingTable").getElementsByTagName("tr");
                for (let i = 1; i < tr.length; i++) {
                    tr[i].style.display = tr[i].getElementsByTagName("td")[1].textContent.toLowerCase().includes(filter) ? "" : "none";
                }
            }
            </script>
        </body></html>"""

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("✅ 週間ランキング更新完了")

    except Exception as e:
        print(f"❌ エラー: {e}")
        raise e 

if __name__ == "__main__":
    run_ranking()
