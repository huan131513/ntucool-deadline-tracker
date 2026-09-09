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
