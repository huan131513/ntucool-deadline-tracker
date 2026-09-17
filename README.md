# NTUCOOL 作業截止提醒系統

透過 NTUCOOL(Canvas LMS)**官方 API** 抓取所有課程的所有作業截止時間,自動排程檢查,
並在截止日前用 Telegram Bot 發送提醒。不需要爬蟲、不需要輸入帳號密碼。

## 使用說明(快速上手)

**⚠️ 注意:核心功能(讀 Chrome cookie、抓 Canvas 資料、網頁面板)macOS / Windows 都能跑,但只有 macOS 有完整實測過的自動排程(`launchd`)。Windows 目前只支援下面的「手動模式」,還沒有對應的自動排程步驟,詳見下方 [Windows 版設定步驟](#windows-版設定步驟手動模式)。**

這**不是下載下來就能直接跑**的工具,每個人要在自己的電腦上照下面步驟設定一次,全部指令都在專案根目錄下執行。整個流程大約 10~15 分鐘,做完就能用網頁面板手動操作(不裝 Telegram、不設定自動排程也完全沒問題,見下方[系統限制](#系統限制))。

下面是 **macOS** 版步驟;用 **Windows** 的話直接跳到 [Windows 版設定步驟](#windows-版設定步驟手動模式)。

### Step 0. 前置需求

- **Chrome 瀏覽器**,而且平常會用它登入 NTUCOOL(`"chrome"` 認證模式要讀它的 cookie)
- **Python 3**(`python3 --version` 確認有裝)
- **Node.js / npm**(build 前端要用,`node -v` 確認有裝)

### Step 1. 下載專案、安裝 Python 套件

```bash
git clone https://github.com/huan131513/ntucool-deadline-tracker.git
cd ntucool-deadline-tracker

# 建立虛擬環境(資料夾 .venv 會在 repo 裡)
python3 -m venv .venv

# 啟動虛擬環境
source .venv/bin/activate

# 確認確實指向 repo 內的 python
which python     # 應該顯示 .../ntucool-deadline-tracker/.venv/bin/python

# 安裝依賴
pip install --upgrade pip
pip install -r requirements.txt

# 之後要離開虛擬環境時
# deactivate
```

### Step 2. 建立自己的設定檔

```bash
cp config.example.json config.json
```

打開 `config.json` 編輯:
- `canvas_auth_mode` 保持 `"chrome"` 就好,不用改
- `telegram_bot_token` / `telegram_chat_id`:**選配**,留空(`""`)也能用,只是不會發 Telegram 通知。想開通知的話,照下方[第 2 節](#2-建立-telegram-bot選配)申請
- `canvas_base_url`:如果不是台大 `cool.ntu.edu.tw`,才需要改

### Step 3. 用 Chrome 登入一次 NTUCOOL

在 Chrome 裡打開 https://cool.ntu.edu.tw 並登入(平常怎麼登入就怎麼登入),讓本機瀏覽器留著一個有效的 session。這一步之後,程式才能讀到有效的 cookie。

順便看一眼你當前google帳號的編號：在網址輸入 `Chrome://version`，找到「設定檔路徑」 例如：	/Users/pengzihuan/Library/Application Support/Google/Chrome/Default

如果最後是profile XX，則到本專案資料夾的config.json設定 "canvas_chrome_profile": "Profile XX"。

### Step 4. Build 前端

```bash
cd frontend
npm install
npm run build
cd ..
```

### Step 5. 啟動,打開網頁面板

```bash
python3 app.py
```

打開瀏覽器到 http://localhost:5050 ,就能看到作業/考試清單、日曆,並手動點:
- **「重新整理」**:去 Canvas 抓最新資料
- **「發送 Telegram 通知」**:手動發一次未完成作業清單(沒設定 Telegram 的話這顆按鈕會是灰色,滑鼠移上去會顯示原因)

**這一步就是終點,不一定要往下設定自動排程。** 想每次用都自己跑一次 `python3 app.py`(或用 `nohup python3 -u app.py &` 丟到背景,關掉終端機也不會被砍掉),用完 `Ctrl+C` 關掉即可 —— 純手動使用,系統一樣能正常運作,差別只是沒有自動幫你檢查/推播提醒。

如果想要「每小時自動檢查、快到期自動用 Telegram 推播提醒」,才需要往下看[第 5 節](#5-排程自動執行macos-launchd)設定 macOS `launchd`(僅支援 macOS)。

## Windows 版設定步驟(手動模式)

跟 macOS 版邏輯完全一樣(讀 Chrome cookie → 打 Canvas API → 網頁面板),只是指令語法換成 PowerShell,而且**目前沒有排程自動化**(`launchd` 是 macOS 專屬,Windows 要嘛用[工作排程器自己設定](#系統限制)每小時打 `/api/notify`,要嘛就跟這裡一樣純手動點按鈕)。

### 這些指令要打在哪裡?(沒用過 Terminal / VSCode 也沒關係)

下面每一段灰色的程式碼區塊,都是要打開一個叫 **PowerShell** 的黑底/藍底視窗,把整段貼進去、按 Enter 執行——不是打在瀏覽器或記事本裡。

**打開 PowerShell 的方法(擇一):**

- 按 **開始鍵**(⊞),直接打字 `powershell`,點第一個結果「Windows PowerShell」
- 或是等你把專案資料夾準備好之後(見下面 Step 1),打開那個資料夾的 **檔案總管**,點一下最上面的**網址列**(顯示資料夾路徑的那一條),整行反白後直接打 `powershell` 再按 Enter——會開一個「已經在這個資料夾裡」的 PowerShell 視窗,省去自己 `cd` 切換路徑的麻煩,**這個方法最推薦**

**怎麼「貼上」指令:** 在你自己的檔案裡把整段程式碼**複製**起來,回到 PowerShell 視窗,**按右鍵**(不是 `Ctrl+V`,舊版 PowerShell 右鍵才是貼上;新版 Windows Terminal 兩種都可以)就會貼上並自動一行行執行。以 `#` 開頭的是**註解**,說明用的,貼進去也不會出錯,可以不用管它。

**全程只需要一個 PowerShell 視窗**,不用開好幾個,除非某個步驟特別註明「另開一個視窗」。

### Step 0. 前置需求

需要 **Chrome 瀏覽器**(平常用它登入 NTUCOOL,這個要自己去官網裝)、**Python 3**、**Node.js**、**Git**(可選)。後面三個 Windows 10/11 都可以直接用內建的 `winget` 指令安裝,不用自己上網找安裝檔、按下一步:

打開 PowerShell(見上面說明),整段貼上執行:
```powershell
winget install --id Python.Python.3.12 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Git.Git -e
```
每個套件安裝時都會跳出確認視窗,點**允許/是**即可。全部裝完後,**關掉這個 PowerShell 視窗、重新開一個新的**(這樣新裝的指令才會被系統認得到),貼上這段確認都裝好了:
```powershell
python --version
node -v
git --version
```
三行都要印出版本號,沒有印出來或出現「不是內部或外部命令」,代表對應那套件沒裝成功,重跑一次上面的 `winget install` 那一行。

> 沒有 `winget` 指令(通常是很舊的 Windows 版本)?改成手動下載安裝:[python.org/downloads](https://www.python.org/downloads/)(安裝時**務必勾選「Add python.exe to PATH」**)、[nodejs.org](https://nodejs.org/)(選 LTS 版本)。Git 也可以跳過不裝,改用下面 Step 1 的「不用 Git」版本。

### Step 1. 下載專案、安裝 Python 套件

**如果沒裝 Git(推薦給不熟悉這些工具的人):**
1. 瀏覽器打開 https://github.com/huan131513/ntucool-deadline-tracker
2. 點右上角綠色的 **Code** 按鈕 → **Download ZIP**
3. 到「下載」資料夾把這個 zip **右鍵 → 全部解壓縮**,解壓縮後會有一個 `ntucool-deadline-tracker-master` 資料夾,建議把它移到比較好找的地方(例如桌面)
4. 打開這個資料夾,照上面「打開 PowerShell 的方法」第二種,在網址列打 `powershell` 開啟 PowerShell(這樣就已經站在這個資料夾裡了,不用 `cd`)

**如果有裝 Git:**
```powershell
git clone https://github.com/huan131513/ntucool-deadline-tracker.git
cd ntucool-deadline-tracker
```

**兩種方式都完成後,在同一個 PowerShell 視窗繼續貼這段:**

```powershell
# 建立虛擬環境(資料夾 .venv 會在 repo 裡)
python -m venv .venv

# 啟動虛擬環境
.venv\Scripts\Activate.ps1

# 如果上面那行說「不允許執行指令碼」,先跑這行放行(只影響目前這個 PowerShell 視窗),
# 再重跑一次上面那行 .venv\Scripts\Activate.ps1:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 安裝依賴
pip install --upgrade pip
pip install -r requirements.txt

# 之後要離開虛擬環境時
# deactivate
```

執行成功的話,PowerShell 提示字元前面會多一個 `(.venv)` 字樣,代表虛擬環境已經啟動。

### Step 2. 建立自己的設定檔

```powershell
copy config.example.json config.json
```

回到 **檔案總管**,打開專案資料夾,找到剛剛產生的 `config.json`,**右鍵 → 開啟檔案 → 記事本**(如果選單有「編輯」也可以直接點,一樣是記事本):
- `canvas_auth_mode` 保持 `"chrome"` 就好,不用改
- `telegram_bot_token` / `telegram_chat_id`:選配,留空也能用,詳見上方[第 2 節](#2-建立-telegram-bot選配)
- `canvas_base_url`:不是台大才需要改

改完記得 **Ctrl+S 存檔**,再關掉記事本。

### Step 3. 用 Chrome 登入一次 NTUCOOL

在 Chrome 打開 https://cool.ntu.edu.tw 並登入。如果之後抓不到 cookie,先看下方[「抓不到 cookie」那個可展開區塊](#chrome預設推薦)排查是不是 Chrome Profile 不對(`chrome://version` 那個方法,Windows/macOS 通用)。

### Step 4. Build 前端

```powershell
cd frontend
npm install
npm run build
cd ..
```

### Step 5. 啟動,打開網頁面板

```powershell
python app.py
```

跑了之後**這個 PowerShell 視窗不會動、也不會跳新畫面出來,看起來像卡住,這是正常的**——它正在背景常駐執行,**不要關掉這個視窗**,只要它開著,網站就能用。

打開瀏覽器,網址列輸入 `http://localhost:5050`,就會看到網頁面板,用法跟 macOS 版一樣(重新整理 / 發送 Telegram 通知)。

不想用了的話,回到那個 PowerShell 視窗按 `Ctrl+C` 停掉,或直接把視窗關掉即可。下次要用,重新打開 PowerShell(記得先 `.venv\Scripts\Activate.ps1` 啟動虛擬環境)再跑一次 `python app.py` 就好,不用重新走一遍前面所有步驟。

<details>
<summary>Windows 上 Chrome cookie 讀不到、跳「需要系統管理員權限」?(點開看已知問題)</summary>

較新版 Chrome(約 2024 年中之後)在 Windows 上加了一層叫 **App-Bound Encryption** 的保護機制,cookie 的解密金鑰綁定到 Chrome 自己的系統服務,舊版 `browser_cookie3` 可能因此讀取失敗,錯誤訊息類似:
```
This operation requires admin. Please run as admin.
```

**先試這個(最可能解決):**
```powershell
pip install --upgrade browser_cookie3
```
升級後新版套件通常能正確處理這個機制,不需要真的用系統管理員權限執行。

**如果升級沒用:**
1. 完全關閉 Chrome(工作管理員裡確認沒有殘留的 `chrome.exe` 行程)再重跑一次
2. 改用 `"cookie"` 手動模式(見上方[說明](#cookie手動備援)),繞開這個相容性問題,代價是 cookie 每天要手動複製貼上一次

</details>

## 系統限制

- **只能在本機執行,無法部署到雲端**(Vercel、Render 等):`"chrome"` 認證模式是直接讀取本機 Chrome 的 cookie 資料庫,雲端環境沒有這份資料,詳見下方[取捨記錄](#為什麼是這個架構認證方式的取捨記錄)方案 5、7
- **排程自動執行(`launchd`)僅支援 macOS**。Windows/Linux 沒有 `launchd`,若要在其他系統上自動排程,需要自行改用 Windows工作排程器/cron 之類的替代方案,或退回手動打開網頁面板按「重新整理」
- **必須本機裝有 Chrome、且平常有用它登入 NTUCOOL**,`"chrome"` 認證模式才抓得到有效 cookie；cookie 有效期由 NTUCOOL 伺服器決定,過期後需要重新登入一次 Chrome,程式不會、也不能自動幫你重新登入(不存密碼,見下方安全性備註)
- **不是「下載即用」**,每個人都要建立自己的 `config.json`(內含各自的 Telegram bot token)並 build 一次前端,`.gitignore` 已排除這些個人設定與資料檔案
- **考試資訊的準確度有限**:除了 Quizzes / Calendar Events 這種結構化資料,「公告關鍵字掃描」只是低信度的關鍵字比對提示,不保證正確,務必點進原始公告確認
- **只鎖定 NTUCOOL(台大 Canvas)預設站台**,若要用在其他學校的 Canvas 站台,需自行修改 `canvas_base_url`;若該站台本身有開放個人 Access Token,可改用更單純穩定的 `"token"` 認證模式(見下方)

## 1. 取得認證方式

**NTUCOOL 不支援 Canvas 原生的個人 Access Token**(參考 [kc0506/ntucool](https://github.com/kc0506/ntucool) 專案的說明),所以設定頁面「功能選項」裡不會有「已核准的整合 / New Access Token」這個區塊,這是正常的,不是你少看到什麼。

改用「登入後的 Session Cookie」來認證 —— 一樣是打 Canvas 官方 REST API,只是認證用 cookie 取代 token。**程式完全不會經手、也不會儲存你的帳號密碼**。有三種模式,用 `config.json` 的 `canvas_auth_mode` 切換:

<details>
<summary>這個 cookie 是誰做的?怎麼運作的?(點開看流程)</summary>

Cookie 是 **NTUCOOL 伺服器**在你用 Chrome 登入的當下製作、發給瀏覽器的,我們的程式從頭到尾沒有參與製作,也不知道你的帳密:

```
你在 Chrome 登入 ntucool.ntu.edu.tw(帳密驗證)
    │
    ▼
NTUCOOL 伺服器驗證成功 → 產生一組 session cookie → 透過 Set-Cookie 交給瀏覽器
    │
    ▼
Chrome 把這個 cookie 存進本機的 cookie 資料庫
    │  (以後瀏覽器造訪同網域都會自動附上,伺服器才認得你是誰)
    ▼
main.py 用 browser_cookie3 讀出這個現成的 cookie
    │  塞進 requests.Session,去打 Canvas 官方 API
    ▼
main.py 拿到 JSON 資料 → 整理成 dashboard_data.json
    ▼
app.py 讀 dashboard_data.json,包成 /api/state 這種乾淨的 JSON 回應
    ▼
React 前端 fetch("/api/state") 拿到的是「整理過的作業/考試資料」
```

**重點:cookie 只在後端 Python 這一層活動,從未流向前端。** 前端(React)和後端(`app.py`)之間走的是完全獨立的本機 API(`/api/state`、`/api/refresh`…),回傳內容只有作業名稱、截止日這類業務資料,不含任何 Canvas 憑證,瀏覽器端也拿不到、看不到那組 cookie。

</details>

### `"chrome"`(預設,推薦)

程式直接讀取你本機 Chrome 目前登入 NTUCOOL 的 session cookie,**不用手動複製貼上**。只要你平常有用 Chrome 登入 NTUCOOL,排程執行時就會自動抓到有效 cookie。

- 只能在**這台電腦本機**執行(讀的是本機 Chrome 的資料),沒辦法部署到 Vercel 之類的雲端服務
- 第一次執行時,macOS 可能會跳出鑰匙圈(Keychain)授權視窗要求解密 Chrome cookie,**務必點「永遠允許」**並輸入電腦密碼確認,不要點「拒絕」或只點一次性的「允許」
- 如果你很長一段時間沒有在 Chrome 裡開過 NTUCOOL、cookie 已失效,程式會報錯提示你重新登入一次

<details>
<summary>抓不到 cookie,但確定 NTUCOOL 有登入、Chrome 也有 cookie?可能是 Chrome 設定檔(Profile)不對(點開看解法)</summary>

`browser_cookie3` 預設**只讀 Chrome 的 `Default` 這個設定檔**,如果你電腦上開了多個 Chrome Profile(右上角頭像切換的那個),而 NTUCOOL 是登入在別的 Profile(例如 `Profile 12`),`Default` 裡面根本沒有那筆 cookie,程式就會回報「找不到 cookie」——即使 Chrome 裡明明看得到。

**先確認是不是這個原因:**

在你實際登入 NTUCOOL 的那個 Chrome 視窗裡,網址列打開 `chrome://version`,看「設定檔路徑(Profile Path)」結尾:
- 結尾是 `.../Chrome/Default` → 不是這個問題,要往別的方向查
- 結尾是 `.../Chrome/Profile 12`(或其他編號)→ 就是這個,往下看怎麼設定

**解法 A(最簡單):換到 Default 這個 Profile 重新登入一次**

用 `chrome://version` 找到哪個視窗才是 `Default`,在那個視窗裡重新登入 https://cool.ntu.edu.tw,之後就抓得到了。

**解法 B:告訴程式讀哪個 Profile**

在 `config.json` 加一行(`canvas_chrome_profile` 填 Profile 的資料夾名稱,不是帳號名稱):
```json
"canvas_chrome_profile": "Profile 12"
```
存檔後重新整理網頁 / 重跑 `python3 main.py --list` 即可。

**額外小工具:** 不想一個一個開視窗找,可以在終端機跑這段,列出每個 Profile 資料夾對應的帳號名稱:
```bash
python3 -c "
import json, os
path = os.path.expanduser('~/Library/Application Support/Google/Chrome/Local State')
with open(path) as f:
    data = json.load(f)
for folder, info in data['profile']['info_cache'].items():
    print(folder, '->', info.get('user_name') or info.get('gaia_name') or info.get('name'))
"
```

</details>

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

## 2. 建立 Telegram Bot(選配)

> Telegram 通知是**選配功能**。`config.json` 裡的 `telegram_bot_token` / `telegram_chat_id` 留空(`""`)即可 —— 網頁面板、`重新整理`、作業/考試列表、日曆等其他功能都不受影響,只有「發送 Telegram 通知」按鈕會自動變成灰色不可點(滑鼠移上去會顯示原因),排程的門檻通知也會自動略過,不會報錯。如果只是想先體驗網頁面板,可以跳過這一整節直接到[第 3 節](#3-設定專案)。

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

> ⚠️ **`ProgramArguments` 裡的 `-u` 不要拿掉**:那是讓 Python 用「無緩衝」模式輸出。少了它,`app.py` 是個一直不會結束的常駐行程,`print()`/`log()` 的內容會卡在記憶體緩衝區裡,`web.log` 可能永遠看不到任何一行 AUTH OK/FAILED 紀錄,即使程式其實跑得正常——這是實際踩過的坑,錯誤現象很隱蔽(服務看起來正常運作,就是 log 是空的)。

### 想看存取 Canvas 的紀錄?

```bash
tail -f web.log                              # 即時看全部輸出
grep -E "AUTH|Telegram|reminder|digest" web.log   # 篩掉每次前端輪詢 /api/progress 的雜訊,只看真正存取資料/發送通知的事件
```

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
