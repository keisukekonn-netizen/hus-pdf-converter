---
title: 学振PDF読み取り変換Web
emoji: 📄
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
pinned: false
license: mit
short_description: Convert Kakenhi PDFs into text-readable PDFs (HUS)
---

# 学振PDF読み取り変換Web

学振（科研費電子申請 / IOWebDOC）が出力するPDFは、表示はできてもツールによって**テキスト抽出に失敗**することがあります。  
このアプリは、見た目を保ったまま **Unicode テキスト層**を付与した PDF に変換します。

## 研究者向け（使い方）

1. この Space の URL を開く
2. （案内がある場合）共有パスワードを入力
3. 学振からダウンロードした PDF をアップロード
4. 「変換する」→ `*_readable.pdf` をダウンロード

## ローカル起動（Web UI）

```powershell
cd "....\科研費支援フォルダ\学振PDF読み取り変換Web"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

ブラウザで `http://127.0.0.1:7860` を開きます。

## ローカル変換（コマンドライン）

```powershell
python convert_cli.py "申請書.pdf" -o .\output
```

## Hugging Face Spaces へのデプロイ

1. [Hugging Face](https://huggingface.co/) でアカウント作成（無料）
2. **New Space** → SDK: **Gradio** / Hardware: **CPU basic（無料）**
3. このフォルダのファイル（`app.py`, `converter.py`, `requirements.txt`, `packages.txt`, `README.md`）を Space にアップロードまたは Git push
4. Space の **Settings → Variables** で任意設定:
   - `ACCESS_PASSWORD` … 共有パスワード（推奨）
5. 公開 URL を研究者へ共有

`packages.txt` により Linux 上に日本語フォント（Noto CJK）が入ります。

## 変換の仕組み（概要）

1. 各ページを画像として描画（帳票レイアウト維持）
2. PyMuPDF で位置付きテキストを抽出
3. 同じ座標に不可視の Unicode テキストを埋め込み

## 注意

- 申請書は機微情報です。信頼できる運用でのみ公開してください。
- 無料 Space はアイドル時にスリープし、初回起動に時間がかかることがあります。
- アップロードファイルは変換処理後に一時領域から削除します（永続保存しません）。
