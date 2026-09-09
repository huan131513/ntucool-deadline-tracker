# NTUCOOL 作業截止提醒系統

透過 NTUCOOL(Canvas LMS)**官方 API** 抓取所有課程的所有作業截止時間,自動排程檢查,
並在截止日前用 Telegram Bot 發送提醒。不需要爬蟲、不需要輸入帳號密碼。

## 1. 取得認證方式

**NTUCOOL 不支援 Canvas 原生的個人 Access Token**(參考 [kc0506/ntucool](https://github.com/kc0506/ntucool) 專案的說明),所以設定頁面「功能選項」裡不會有「已核准的整合 / New Access Token」這個區塊,這是正常的,不是你少看到什麼。

改用「登入後的 Session Cookie」來認證 —— 一樣是打 Canvas 官方 REST API,只是認證用 cookie 取代 token。**程式完全不會經手、也不會儲存你的帳號密碼**。有三種模式,用 `config.json` 的 `canvas_auth_mode` 切換:

### `"chrome"`(預設,推薦)

程式直接讀取你本機 Chrome 目前登入 NTUCOOL 的 session cookie,**不用手動複製貼上**。只要你平常有用 Chrome 登入 NTUCOOL,排程執行時就會自動抓到有效 cookie。

- 只能在**這台電腦本機**執行(讀的是本機 Chrome 的資料),沒辦法部署到 Vercel 之類的雲端服務
- 第一次執行時,macOS 可能會跳出鑰匙圈(Keychain)授權視窗要求解密 Chrome cookie,允許即可(可選「永遠允許」減少之後的提示)
- 如果你很長一段時間沒有在 Chrome 裡開過 NTUCOOL、cookie 已失效,程式會報錯提示你重新登入一次

### `"cookie"`(手動備援)

如果 `"chrome"` 模式在你的環境行不通(例如你不是用 Chrome、或想部署到雲端),可以手動複製 cookie:

1. 用你平常的方式登入 https://cool.ntu.edu.tw(走學校 SSO)
2. 打開瀏覽器開發者工具(F12)→ **Network / 網路** 分頁
3. 重新整理頁面,或點進任一堂課程
4. 找一個發往 `cool.ntu.edu.tw` 的請求 → **Headers** → **Request Headers** → 複製 `Cookie:` 後面**完整的一長串值**
5. 貼到 `config.json` 的 `canvas_cookie`,並把 `canvas_auth_mode` 改成 `"cookie"`

> ⚠️ 這個 cookie 大約 24 小時左右會過期,過期後程式會提示你重新登入、重新複製貼上。

### `"token"`

如果你的 Canvas 站台其實有開放個人 Access Token,把 `canvas_auth_mode` 改成 `"token"` 並填 `canvas_access_token` 即可。

## 2. 建立 Telegram Bot

1. Telegram 搜尋 **@BotFather**,傳送 `/newbot`,依指示取得 **bot token**
2. 跟你剛建立的 bot 說一句話(例如 `/start`),讓它能傳訊給你
3. 瀏覽器打開:
   `https://api.telegram.org/bot<你的BOT_TOKEN>/getUpdates`
   在回傳的 JSON 裡找 `"chat":{"id": 123456789, ...}`,那組數字就是你的 **chat_id**

## 3. 設定專案

```bash
cd ~/Documents/GitHub/ntucool-deadline-tracker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
```

編輯 `config.json`,填入:
- `canvas_auth_mode` 預設是 `"chrome"`,不用額外設定,保持平常登入 Chrome 的習慣即可
- `telegram_bot_token` / `telegram_chat_id`:第 2 步拿到的值
- `remind_before_days`:想在截止前幾天收到提醒,例如 `[7, 3, 1]`
- `canvas_base_url`:如果不是 `cool.ntu.edu.tw` 請自行修改

## 4. 測試

```bash
# 先確認能抓到所有作業(不會送出任何通知)
python3 main.py --list

# 模擬跑一次提醒邏輯,只印出不會真的發送/寫入狀態
python3 main.py --dry-run

# 正式跑一次(會發送 Telegram 訊息、並記錄已通知過的項目到 state.json)
python3 main.py
```

## 5. 排程自動執行(macOS launchd)

推薦用 `launchd`(比 cron 更能配合 Mac 睡眠/喚醒)。需要**兩個服務**,因為排程現在是打網頁面板的 API,而不是直接跑 `main.py`(這樣 CLI 跟網頁按鈕的通知邏輯才是同一份程式碼路徑):

1. **`com.example.ntucool-web`**:常駐服務,讓 `app.py` 一直在背景跑(`RunAtLoad` + `KeepAlive`,掛掉會自動重啟)
2. **`com.example.ntucool-notify`**:每小時觸發一次,對著 `com.example.ntucool-web` 打 `curl -X POST http://127.0.0.1:5050/api/notify`

範本在 [`launchd/`](launchd/) 資料夾,套用步驟:

```bash
cp launchd/com.example.ntucool-web.plist ~/Library/LaunchAgents/com.yourname.ntucool-web.plist
cp launchd/com.example.ntucool-notify.plist ~/Library/LaunchAgents/com.yourname.ntucool-notify.plist
```

編輯這兩個檔案:
- 把 `Label` 裡的 `com.example` 換成你自己的識別字串(跟檔名一致)
- 把 `/ABSOLUTE/PATH/TO/ntucool-deadline-tracker` 換成你專案的實際絕對路徑

然後載入:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yourname.ntucool-web.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yourname.ntucool-notify.plist
```

> ⚠️ **第一次載入新的 LaunchAgent,macOS 可能會跳通知或要你去「系統設定 → 一般 → 登入項目與延伸功能」手動核准**,沒核准的話服務會靜默失敗(`launchctl print` 會顯示 `last exit code = 78: EX_CONFIG`,且完全沒有 log 輸出)。核准後重新 `launchctl bootstrap` 一次即可。

> 因為程式會用 `state.json` 記錄「哪個作業的哪個提醒門檻已經發過」,所以就算排程跑很頻繁,
> 同一個提醒也只會收到一次,不會洗版。

> ⚠️ **限制**:`"chrome"` 模式只能在這台裝有 Chrome 的電腦本機執行,無法部署到 Vercel 等雲端服務(讀不到你本機的瀏覽器資料)。

## 6. 網頁面板(React + Flask)

除了排程自動提醒,還有一個本機網頁面板可以手動觸發抓取、看作業/考試清單、手動發 Telegram 通知。前端是 React(Vite 建置),後端是 Flask 純 JSON API。

```bash
# 第一次使用,或改了前端程式碼之後:
cd frontend
npm install
npm run build      # 產出 frontend/dist/,Flask 會直接讀這裡

# 回到專案根目錄啟動後端(同時會把上面 build 好的前端一起端出去):
cd ..
source .venv/bin/activate
python3 app.py
```

打開 http://localhost:5050,兩顆按鈕:「重新整理」(重新走一次 chrome cookie → Canvas API 抓取)、「發送 Telegram 通知」(手動跑一次跟排程一樣的門檻檢查)。

**只改前端外觀/邏輯時**,不用每次重新 build,另開一個 terminal 用 Vite 的開發伺服器(有熱更新):

```bash
cd frontend
npm run dev    # 開 http://localhost:5173,API 請求會自動 proxy 到 :5050 的 Flask
```

Flask 那邊(`python3 app.py`)要保持在跑,因為它是真正打 Canvas API 的地方 —— Vite dev server 只負責前端畫面,不會自己讀 Chrome cookie。

## 檔案說明

| 檔案 | 用途 |
|---|---|
| `main.py` | 核心邏輯:抓課程/作業/考試、比對截止日、發送 Telegram(CLI 與網頁面板共用) |
| `app.py` | 網頁面板的後端,純 JSON API(`/api/state`、`/api/refresh`、`/api/notify`),同時 serve 前端 build 出來的靜態檔 |
| `frontend/` | React 前端(Vite),原始碼在 `frontend/src/`,build 產物在 `frontend/dist/`(已加入 .gitignore) |
| `config.example.json` | 設定檔範本 |
| `config.json` | 你的真實設定(內含 token,已加入 .gitignore,不會被 git 追蹤) |
| `state.json` | 記錄已發送過的提醒,避免重複通知(執行後自動產生) |
| `dashboard_data.json` | 網頁面板的資料快取(已加入 .gitignore,內含你的真實課程/作業資料) |

## 安全性備註

- 你的 Canvas token 與 Telegram bot token 只存在本機的 `config.json`,不會上傳到任何地方。
- `.gitignore` 已排除 `config.json` 與 `state.json`,如果你要把這個專案推上 GitHub,記得再三確認沒有把 token 誤 commit 進去。

## 為什麼是這個架構:認證方式的取捨記錄

這個專案的認證方式(`canvas_auth_mode`)繞了一圈才定案,記錄下每個嘗試過的方案、為什麼放棄或採用,方便之後回頭理解,也給遇到同樣問題的人參考。

| # | 嘗試方案 | 為什麼考慮它 | 為什麼放棄 / 採用原因 | 結果 |
|---|---|---|---|---|
| 1 | 爬蟲(直接解析網頁 HTML) | 最直覺的做法 | 沒有走官方管道,穩定性差、容易因網頁改版壞掉,也更容易被判定為異常流量 | ❌ 放棄,改用官方 Canvas REST API |
| 2 | Canvas 個人 Access Token | 官方支援的標準認證方式,最安全乾淨 | 實測發現 NTUCOOL 設定頁沒有「已核准的整合」區塊 —— 該校 Canvas 站台**未開放**學生自行產生 token(參考 [kc0506/ntucool](https://github.com/kc0506/ntucool) 專案的說明佐證) | ❌ 此路不通,非技術選擇而是校方限制 |
| 3 | 手動複製 Session Cookie 貼上 | Token 不通後的替代方案,一樣是打官方 API 只是換認證方式 | 可行,但 cookie 大約會過期(實測發現它是「session cookie」沒有寫死到期時間,但伺服器端 session 逾時政策不明),過期後需要你手動重新登入、重新複製貼上 | ⚠️ 保留作為備援模式(`canvas_auth_mode: "cookie"`),但太依賴人工 |
| 4 | 自動化模擬 NTU SSO 登入(程式存帳密,過期自動重新登入拿新 cookie) | 想徹底解決 cookie 過期要手動處理的問題 | **資安風險過高**:程式要存你的 NTU 密碼(等同信箱/選課系統/成績單鑰匙);若帳號有雙因素驗證,自動化會直接卡死;頻繁自動登入行為可能被學校系統判定異常而鎖帳號 | ❌ 主動放棄,判斷風險大於便利性 |
| 5 | 部署到 Vercel(雲端) | 想要不依賴自己電腦、隨時隨地都能跑 | 三個疊加問題:①`chrome` 模式讀的是本機瀏覽器資料,雲端環境完全碰不到;②Vercel serverless function 無狀態,`state.json` 防重複通知需要額外外接資料庫;③改用手動複製的 cookie 存進 Vercel 環境變數,等於把等同密碼的憑證放到第三方雲端服務,風險跟方案 4 同一個等級,而且 cookie 一過期一樣要手動回來更新,雲端化沒有解決根本問題 | ❌ 放棄,回到本機執行 |
| 6 | 瀏覽器書籤(Bookmarklet)一鍵回傳 cookie | 想减少「開 DevTools 找 Cookie 值」的手動複製貼上步驟 | **技術上直接不可行**:實測確認 `_legacy_normandy_session` 等關鍵 session cookie 被標記 `HttpOnly`,瀏覽器規範就是不讓網頁 JS(`document.cookie`)讀到這種 cookie —— 這正是 HttpOnly 設計出來要防的攻擊手法 | ❌ 硬性技術限制,非取捨 |
| 7 | 本機用 `browser_cookie3` 直接讀 Chrome 現有 cookie 存放區 | 既不用存密碼、也不用手動複製貼上,自動抓「當下」有效的登入狀態 | 完全解決前面所有痛點:不存密碼(比方案 4 安全)、不用手動操作(比方案 3 方便)、技術上真正可行(不像方案 6 撞牆)。唯一代價是**只能在本機執行**,徹底排除了方案 5 的雲端化可能性 | ✅ **最終採用**,設為預設認證模式(`canvas_auth_mode: "chrome"`) |
| 8 | 純 React 前端、完全不要後端程式 | 想要更現代化的架構,不想維護 Python | **技術上不可能**:瀏覽器分頁裡的 JS 沒有檔案系統權限讀不到本機 Chrome 的 cookie 資料庫,而且瀏覽器會擋 JS 手動設定 `Cookie` request header(受保護標頭),`cool.ntu.edu.tw` 也沒開放跨網域 CORS —— 這兩件事都需要一個能存取本機檔案、且不受瀏覽器安全沙盒限制的常駐程式 | ❌ 確認不可行,保留精簡 Flask JSON API 作後端 |

**貫穿全部取捨的共同判斷原則:**

1. **官方 API 優先於爬蟲**:無論後面怎麼調整認證方式,資料存取的手段從頭到尾都是打 Canvas 官方 `/api/v1/...` 端點,從未改用解析 HTML 這種脆弱又容易被判定異常的做法。
2. **帳密永遠不進入自動化流程**:方案 4(自動登入存密碼)是唯一一個因為「牽涉密碼」被直接排除的選項,即使它能解決 cookie 過期的根本問題,也判斷不值得用帳號安全去換。
3. **技術硬限制 vs 工程取捨要分開判斷**:方案 2(Token 不開放)、方案 6(HttpOnly 擋書籤)、方案 8(瀏覽器沙盒擋讀 cookie/設 header)這三個是「做不到」,不是「不想做」——分辨清楚才能不浪費時間在錯的方向上重複嘗試。
4. **「本機執行」是最終方案付出的代價**:方案 7 能同時滿足安全又方便,但换來系統無法雲端化(方案 5)這個限制,這是目前架構下權衡出來、主動接受的取捨,不是意外。
