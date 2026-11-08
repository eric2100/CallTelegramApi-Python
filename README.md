# CallTelegramApi-Python

獨立的 Python 版 Telegram 命令列工具。延續 [Pascal 版](https://github.com/eric2100/CallTelegramApi) 的文字／檔案參數與 INI 設定格式，支援自訂 Telegram Bot API、中文訊息與檔名、1 GB 串流上傳。

## Python 執行

需要 Python 3.10 以上。Windows 範例：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item CallTelegram.ini.example CallTelegram.ini
```

編輯 `CallTelegram.ini`，填入自己的 Token 與聊天室 ID：

```ini
[MAIN]
Token=你的機器人Token
SendChatId=你的聊天室ID
ApiBaseUrl=http://127.0.0.1:8081
ConnectTimeout=30000
ReadTimeout=3600000
ProxyServer=
ProxyPort=
```

```powershell
.venv\Scripts\python.exe call_telegram.py "測試訊息"
.venv\Scripts\python.exe call_telegram.py "傳送備份" "D:\Backup\backup.zip"
.venv\Scripts\python.exe call_telegram.py --config "D:\Settings\CallTelegram.ini" "測試訊息"
```

Linux／macOS 使用 `.venv/bin/python`，其餘用法相同。INI 使用 UTF-8，可含 BOM；不會解讀 `%` 插值。

預設讀取程式所在資料夾的 `CallTelegram.ini`，也可用 `--config` 指定。真實設定檔已列入 `.gitignore`。

## 自訂 API 與 1 GB 檔案

`ApiBaseUrl` 填 API 根網址，例如 `http://192.168.1.10:8081` 或 `https://bot-api.example.com/telegram`，不加 `/bot<Token>` 或方法名稱。省略或留空時使用 `https://api.telegram.org`。

1 GB 檔案必須使用啟用 `--local` 的 [Telegram Bot API Server](https://github.com/tdlib/telegram-bot-api)，其支援最高 2000 MB；官方雲端的一般上傳上限為 50 MB。更換網址本身無法提高上限。既有雲端機器人切換前，需按官方流程呼叫 `logOut`；本程式不會自動登出或改動伺服器。若有反向代理，需調整請求大小及逾時限制。

詳見 [Telegram 官方說明](https://core.telegram.org/bots/api#using-a-local-bot-api-server)。

使用 [requests-toolbelt MultipartEncoder](https://toolbelt.readthedocs.io/en/latest/uploading-data.html) 從磁碟串流讀取，避免把 1 GB 檔案一次載入記憶體。`ConnectTimeout`、`ReadTimeout` 單位為毫秒，預設分別為 30 秒及 1 小時；逾時不是整次上傳總時限。

HTTPS 使用憑證驗證，無須舊版 OpenSSL DLL。只有 INI 的 `ProxyServer`／`ProxyPort` 會生效，不讀取環境代理或 `.netrc`。

## 傳送與錯誤處理

先檢查／開啟檔案，再傳送文字，最後上傳檔案。成功輸出 `OK` 並回傳結束碼 `0`；設定、連線或 API 失敗回傳 `1`，參數用法錯誤回傳 `2`。錯誤訊息會遮蔽 Token；不自動重試，也不跟隨重新導向。

若文字已送出而檔案失敗，已送出的文字會保留。手動重跑可能產生重複訊息。

## Windows EXE 打包

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe build.py
```

產生 `dist/CallTelegramApi.exe` 與 `dist/CallTelegramApi-Python-Windows.zip`。解壓後編輯同資料夾內的 `CallTelegram.ini`，不需要安裝 Python：

```powershell
.\CallTelegramApi.exe "傳送備份" "D:\Backup\backup.zip"
```

打包時永遠使用空白範例設定，不會包含開發者的 Token。

GitHub Actions 會在推送 `main`、Pull Request 或手動執行時自動測試 Python 及 EXE（含 1 GiB 上傳），並產生可下載的 Windows 壓縮檔。到儲存庫的 Actions 頁面，開啟成功的執行紀錄後下載 Artifacts。

## 測試

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
$env:TEST_LARGE_UPLOAD = '1'
.venv\Scripts\python.exe -m unittest discover -s tests -v
# 驗證打包後的 EXE
$env:CALL_TELEGRAM_EXE = (Resolve-Path dist\CallTelegramApi.exe).Path
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

測試使用假 Token 和本機 HTTP 模擬伺服器，不會傳送 Telegram 訊息。大檔案測試實際上傳 1 GiB（1,073,741,824 bytes），需暫存磁碟空間；通過只代表客戶端傳輸成功，不代表實際 Telegram 或自架伺服器已收件。
