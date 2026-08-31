# 学振PDF読み取り変換Web（HUS）

学振（科研費電子申請 / IOWebDOC）が出力するPDFは、表示はできてもツールによって**テキスト抽出に失敗**することがあります。  
このアプリは、見た目を保ったまま **Unicode テキスト層**を付与した PDF に変換します。

- GitHub: https://github.com/keisukekonn-netizen/hus-pdf-converter
- 公開先: **Streamlit Community Cloud**（無料）

## 研究者向け（使い方）

1. 共有された Streamlit の URL を開く
2. （案内がある場合）共有パスワードを入力
3. 学振からダウンロードした PDF をアップロード
4. 「変換する」→ `*_readable.pdf` をダウンロード

## ローカル起動（Web UI）

```powershell
cd "....\科研費支援フォルダ\学振PDF読み取り変換Web"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## ローカル変換（コマンドライン）

```powershell
python convert_cli.py "申請書.pdf" -o .\output
```

## Streamlit Community Cloud へのデプロイ

1. https://share.streamlit.io/ で GitHub アカウント連携（無料）
2. **New app** を押す
3. 設定:
   - Repository: `keisukekonn-netizen/hus-pdf-converter`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
4. （推奨）**Advanced settings → Secrets** に次を追加:

```toml
ACCESS_PASSWORD = "ここに共有パスワード"
```

5. Deploy 後の URL を研究者へ共有

## 変換の仕組み（概要）

1. 各ページを画像として描画（帳票レイアウト維持）
2. PyMuPDF で位置付きテキストを抽出
3. 同じ座標に不可視の Unicode テキストを埋め込み

## 注意

- 申請書は機微情報です。信頼できる運用でのみ公開してください。
- 無料枠はアイドル時にスリープし、初回起動に時間がかかることがあります。
- アップロードファイルは変換処理後に一時領域から削除します（永続保存しません）。
