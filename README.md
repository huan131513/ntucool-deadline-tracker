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

## 5. 排程自動執行(macOS)

用 cron 每天早上 8 點跑一次:

```bash
crontab -e
```

加入一行(記得把路徑換成你自己的):

```
0 8 * * * cd ~/Documents/GitHub/ntucool-deadline-tracker && .venv/bin/python main.py >> cron.log 2>&1
```

想更頻繁一點,例如每 6 小時檢查一次:

```
0 */6 * * * cd ~/Documents/GitHub/ntucool-deadline-tracker && .venv/bin/python main.py >> cron.log 2>&1
```

> 因為程式會用 `state.json` 記錄「哪個作業的哪個提醒門檻已經發過」,所以就算排程跑很頻繁,
> 同一個提醒也只會收到一次,不會洗版。

> ⚠️ **限制**:`"chrome"` 模式只能在這台裝有 Chrome 的電腦本機執行,無法部署到 Vercel 等雲端服務(讀不到你本機的瀏覽器資料)。如果你的 Mac 會睡眠,記得在「系統設定 → 電池/節能」開啟「排定的活動可以喚醒電腦」之類的選項,或改用 `launchd` 排程(比 cron 更能配合喚醒),不然電腦睡著時 cron 不會執行。

## 檔案說明

| 檔案 | 用途 |
|---|---|
| `main.py` | 主程式:抓課程/作業、比對截止日、發送 Telegram |
| `config.example.json` | 設定檔範本 |
| `config.json` | 你的真實設定(內含 token,已加入 .gitignore,不會被 git 追蹤) |
| `state.json` | 記錄已發送過的提醒,避免重複通知(執行後自動產生) |

## 安全性備註

- 你的 Canvas token 與 Telegram bot token 只存在本機的 `config.json`,不會上傳到任何地方。
- `.gitignore` 已排除 `config.json` 與 `state.json`,如果你要把這個專案推上 GitHub,記得再三確認沒有把 token 誤 commit 進去。
