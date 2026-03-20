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
    now = datetime.now(JST)
    # 月曜0:00を取得
    last_monday = now - timedelta(days=now.weekday())
    last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return last_monday.astimezone(timezone.utc)

def run_ranking():
    try:
        now_jst = datetime.now(JST)
        start_time_utc = get_last_monday()
        start_time_jst = start_time_utc.astimezone(JST)

        print(f"🚀 高密度・週間集集計開始 (対象: {start_time_jst.strftime('%m/%d %H:%M')} 〜)")
        
        project = scratch3.get_project(PROJECT_ID)
        project.update() 
        user_stats = {}

        # 💡 過密対策：最大50,000件までチェック範囲を拡大
        for offset in range(0, 50000, 40): 
            try:
                comments = project.comments(limit=40, offset=offset)
            except Exception as e:
                print(f"⚠ 取得失敗(offset {offset}): {e}")
                time.sleep(10) # 失敗時は少し長めに待機
                continue

            if not comments: break
            
            stop_signal = False
            for c in comments:
                dt = parse_scratch_date(c.datetime_created)
                
                # 月曜0時より前のデータなら停止
                if dt < start_time_utc:
                    print(f"⏳ 月曜日の境界線({dt})に到達。集計を完了します。")
                    stop_signal = True
                    break
                
                user = get_author_name(c)
                if user not in IGNORE_USERS:
                    if user not in user_stats: user_stats[user] = {"p": 0, "r": 0}
                    user_stats[user]["p"] += 1
                
                # 返信の集計
                try:
                    replies = c.replies()
                    for r in replies:
                        if parse_scratch_date(r.datetime_created) >= start_time_utc:
                            r_user = get_author_name(r)
                            if r_user not in IGNORE_USERS:
                                if r_user not in user_stats: user_stats[r_user] = {"p": 0, "r": 0}
                                user_stats[r_user]["r"] += 1
                except: pass
            
            # ログに進捗を表示（安心感のため）
            if offset % 400 == 0:
                print(f"  ...{offset}件チェック完了")

            if stop_signal: break
            time.sleep(0.1) # 高速化のため待機時間を短縮

        sorted_users = sorted(user_stats.items(), key=lambda x: (x[1]["p"] + x[1]["r"]), reverse=True)

        # --- HTML作成 ---
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Scratch Weekly Ranking (High-Density)</title>
            <style>
                body {{ font-family: sans-serif; background: #eef2f3; padding: 10px; }}
                .container {{ background: white; padding: 20px; border-radius: 15px; max-width: 800px; margin: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }}
                h1 {{ color: #16a085; text-align: center; border-left: 8px solid #16a085; padding: 10px; background: #f9f9f9; }}
                .info {{ text-align: right; color: #7f8c8d; font-size: 0.85em; margin-bottom: 15px; }}
                #search {{ width: 100%; padding: 15px; margin-bottom: 20px; border: 2px solid #16a085; border-radius: 30px; outline: none; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ padding: 12px; border-bottom: 1px solid #eee; }}
                th {{ background: #16a085; color: white; position: sticky; top: 0; }}
                .total-num {{ font-weight: bold; color: #16a085; font-size: 1.1em; }}
                .rank-1 {{ background: #e8f8f5; border: 2px solid #1abc9c; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔥 週間ガチ勢ランキング</h1>
                <div class="info">
                    📅 {start_time_jst.strftime('%m/%d')} 〜 現在 | 🕒 更新: {now_jst.strftime('%H:%M')}
                </div>
                <input type="text" id="search" placeholder="🔍 ユーザー名を検索して順位を確認..." onkeyup="filterTable()">
                <table id="rankingTable">
                    <thead><tr><th>順位</th><th>ユーザー名</th><th>活動合計 (コメント/返信)</th></tr></thead>
                    <tbody>
        """
        for i, (user, stat) in enumerate(sorted_users):
            total = stat["p"] + stat["r"]
            row_class = 'class="rank-1"' if i == 0 else ""
            html_content += f"""
                        <tr {row_class}>
                            <td>{i+1}</td>
                            <td><strong>{user}</strong></td>
                            <td><span class="total-num">{total}</span> <span style="font-size:0.8em;">({stat['p']}/{stat['r']})</span></td>
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
        print(f"✅ 全集計完了！ 対象人数: {len(sorted_users)}人")

    except Exception as e:
        print(f"❌ エラー発生: {e}")
        raise e 

if __name__ == "__main__":
    run_ranking()
