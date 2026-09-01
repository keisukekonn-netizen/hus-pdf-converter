# 学振PDF読み取り変換Web — 科研費AIシステム連携用 引き継ぎ文書

> **目的**: 本ドキュメントは、北海道科学大学 研究推進社会実装センター（HUS）が運用する「学振PDF読み取り変換Web」の仕様・実装・連携方針を、**科研費AIシステム**側の Cursor プロジェクトへ引き継ぐためのものです。  
> **作成日**: 2026-09-01  
> **リポジトリ**: https://github.com/keisukekonn-netizen/hus-pdf-converter

---

## 1. このシステムが解決する問題

### 背景

学振（科研費電子申請 / **IOWebDOC**）から出力される PDF は、Adobe Reader 等では**正常に表示・印刷**できるが、多くのテキスト抽出ツールや AI システムでは**文字として認識できない**（文字化け・空文字・抽出失敗）ことがある。

主な技術的原因:

| 原因 | 説明 |
|------|------|
| ToUnicode マップ不足 | PDF 内のグリフ ID → Unicode 変換表が欠けている |
| 日本語 CID フォント | MS ゴシック系など独自エンコーディングで保存されている |
| 帳票優先設計 | 見た目再現が目的で、機械可読性は設計上の優先事項ではない |

### 本システムの役割

学振 PDF を **「二層構造の読み取り可能 PDF」** に変換する。

1. **視覚層**: 各ページを高解像度ラスター画像として再描画（帳票レイアウト維持）
2. **テキスト層**: PyMuPDF で抽出した文字を、同じ座標に **不可視の Unicode テキスト** として再埋め込み

変換後 PDF（`*_readable.pdf`）は、科研費 AI システムや一般的な PDF テキスト抽出ツールから読み取り可能になる。

---

## 2. システム構成

```
学振PDF読み取り変換Web/
├── converter.py       # ★ コア変換ロジック（連携時はここが重要）
├── streamlit_app.py   # Web UI（Streamlit Community Cloud 用）
├── convert_cli.py     # コマンドライン一括変換
├── requirements.txt   # streamlit>=1.28.0, pymupdf>=1.24.0
└── README.md
```

### デプロイ

- **公開先**: Streamlit Community Cloud（無料）
- **エントリポイント**: `streamlit_app.py`
- **認証**: 環境変数 / Streamlit Secrets の `ACCESS_PASSWORD`（任意）
- **GitHub**: `keisukekonn-netizen/hus-pdf-converter`（`main` ブランチ）

### 運用フロー（現状・研究者向け）

```
学振 PDF → Web アップロード → 変換 → *_readable.pdf ダウンロード → 科研費AI等で利用
```

アップロードファイルは変換後にサーバ上の一時領域から削除される（永続保存しない）。

---

## 3. コア変換ロジック（converter.py）

### 公開 API

```python
from converter import convert_jsps_pdf, convert_to_temp, RENDER_DPI

# 基本変換
output_path, stats = convert_jsps_pdf(
    input_path="申請書.pdf",
    output_path="申請書_readable.pdf",  # 省略時: {stem}_readable.pdf
    render_dpi=216,                     # 省略時: RENDER_DPI (216)
)

# 一時ファイルへ変換（Web/API 向け）
output_path, stats = convert_to_temp(input_path="申請書.pdf")
# 呼び出し側で使用後に output_path を削除すること
```

### 戻り値 stats

```python
{
    "pages": int,              # 総ページ数
    "chars": int,              # 埋め込んだ文字数（全ページ合計）
    "pages_with_text": int,    # テキスト層が付いたページ数
    "font": str,               # 使用フォント（例: "builtin:japan"）
    "render_dpi": int,         # 背景画像の DPI（現在 216）
    "output": str,             # 出力 PDF の絶対パス
}
```

### 変換アルゴリズム（ページ単位）

```
入力 PDF（学振 IOWebDOC 出力）
    │
    ├─ 1. ページを 216 DPI でラスター化（get_pixmap）
    │      → 新 PDF ページに背景画像として挿入
    │
    ├─ 2. 元 PDF から get_text("dict") でテキスト＋座標を抽出
    │      → block → line → span 単位で走査
    │
    └─ 3. TextWriter で同座標に Unicode テキストを書き込み
           → render_mode=3（不可視）で出力
```

### フォント

- 優先: PyMuPDF 組み込み `"japan"` フォント（Unicode 対応が確実）
- フォールバック: 環境変数 `JAPANESE_FONT_PATH` または OS 上の Noto / 游ゴシック / MS ゴシック / メイリオ
- **注意**: 不可視テキスト層用のフォントであり、**見た目（背景画像）のフォントとは無関係**

### 定数

| 定数 | 値 | 意味 |
|------|-----|------|
| `RENDER_DPI` | `216` | 背景ラスター画像の解像度（画質とサイズのバランス） |

---

## 4. 出力 PDF の性質

### 二層構造

| 層 | 内容 | 用途 |
|----|------|------|
| 背景（視覚層） | 216 DPI ラスター画像 | 人間が見る帳票レイアウト |
| 前景（テキスト層） | 不可視 Unicode テキスト（render_mode=3） | 検索・コピー・AI 読み取り |

### 既知の制限

- **OCR ではない**: 元 PDF にテキストデータが存在しない部分（画像のみの欄等）は変換後も空のまま
- **見た目の差**: ラスター化により、元 PDF ビューアと比べ文字がやや太く見えたりフォントが異なって見えることがある（PyMuPDF 描画エンジンの差。座標ずれが主因ではない）
- **座標ずれ**: 不可視テキスト層の選択範囲が視覚テキストと微妙にずれる場合がある（bbox ベースの baseline 推定による）
- **ファイルサイズ**: 216 DPI ラスター化のため、元 PDF より大きくなる
- **処理時間・メモリ**: ページ数に比例。Streamlit Cloud 無料枠では十数ページ程度が目安

---

## 5. 科研費AIシステムとの連携案

### 現状の連携（間接的）

```
研究者 → 学振PDF読み取り変換Web → *_readable.pdf ダウンロード → 科研費AIシステムへ手動アップロード
```

### 連携パターン（推奨順）

#### パターン A: Python モジュールとして直接組み込み（最もシンプル）

科研費AIシステムが Python（Streamlit / FastAPI / Flask 等）であれば、`converter.py` をコピーまたは git submodule で取り込み、PDF アップロード時に自動変換する。

```python
from converter import convert_jsps_pdf

def preprocess_pdf(uploaded_path: Path) -> Path:
    """学振 PDF を AI 読み取り用に前処理"""
    readable_path, stats = convert_jsps_pdf(uploaded_path)
    if stats["chars"] == 0:
        raise ValueError("テキストを抽出できませんでした。画像のみの PDF の可能性があります。")
    return readable_path
```

**メリット**: 追加インフラ不要、レイテンシ最小  
**デメリット**: pymupdf 依存の追加、メモリ使用量増

#### パターン B: 内部 API 化（マイクロサービス）

`converter.py` を FastAPI 等でラップし、HTTP エンドポイントとして公開。

```
POST /convert
  Content-Type: multipart/form-data
  Body: file (PDF)

Response:
  200: application/pdf（変換後 PDF）
  + X-Stats-Pages, X-Stats-Chars 等のヘッダ（任意）
```

科研費AIシステムから HTTP 経由で呼び出す。

**メリット**: 言語・フレームワーク非依存、独立スケール  
**デメリット**: 別サービスの運用が必要

#### パターン C: 既存 Streamlit Web をそのまま利用（現状維持）

科研費AIシステムの UI から変換 Web の URL へリンクし、変換済み PDF を再アップロードしてもらう。

**メリット**: 実装コストゼロ  
**デメリット**: 研究者の手間が残る、UX が分断される

#### パターン D: テキストのみ抽出して JSON で渡す（PDF 再生成不要の場合）

科研費AIシステムが PDF ファイル自体ではなくテキスト内容だけ必要な場合:

```python
import pymupdf

def extract_text_from_jsps(pdf_path: str) -> list[dict]:
    """ページごとのテキスト＋座標を JSON 化"""
    doc = pymupdf.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text_dict = page.get_text("dict")
        pages.append({"page": i + 1, "blocks": text_dict.get("blocks", [])})
    doc.close()
    return pages
```

`*_readable.pdf` を経由せず、直接テキストを AI パイプラインへ渡すことも可能。  
ただし **他ツールとの互換性**（研究者が変換 PDF をダウンロードして使う等）が必要ならパターン A/B を推奨。

---

## 6. 科研費AIシステム側で確認すべきこと

連携実装前に、科研費AIシステム側で以下を確認してください。

1. **PDF 入力方式**: ファイルアップロードか、テキスト直接入力か
2. **テキスト抽出方法**: 自前実装 / PyMuPDF / pdfplumber / LangChain PDFLoader 等
3. **学振 PDF 非対応の症状**: 空文字・文字化け・特定セクションのみ失敗、等
4. **必要な出力**: 変換 PDF ファイルか、プレーンテキスト / 構造化 JSON か
5. **セキュリティ要件**: 申請書は機微情報。変換処理をどこで実行するか（オンプレ / クラウド / ローカルのみ）

### 連携時の品質チェック指標

変換後、以下を確認すると成功判定しやすい:

| 指標 | 目安 |
|------|------|
| `stats["chars"]` | > 0（0 なら変換失敗または画像のみ PDF） |
| `stats["pages_with_text"]` | ≒ `stats["pages"]`（全ページにテキスト層） |
| AI 側での読み取り | 研究目的・研究方法等の主要セクションが正しく取得できる |

---

## 7. 依存関係と環境

```
streamlit>=1.28.0   # Web UI 用（連携時は不要な場合あり）
pymupdf>=1.24.0     # ★ 必須
```

### 環境変数

| 変数 | 用途 |
|------|------|
| `ACCESS_PASSWORD` | Web UI の共有パスワード（任意） |
| `JAPANESE_FONT_PATH` | 日本語フォントの明示指定（任意。通常は builtin:japan で十分） |

### ローカル実行

```powershell
cd "...\学振PDF読み取り変換Web"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Web UI
streamlit run streamlit_app.py

# CLI
python convert_cli.py "申請書.pdf" -o .\output
```

---

## 8. セキュリティ上の注意

- 科研費申請書は**研究内容・個人情報を含む機微情報**
- 現行 Web 版は変換後にファイルを削除するが、**クラウド上で一時的に処理される**
- 科研費AIシステムとの連携では、以下を検討すること:
  - オンプレ / ローカル完結処理（パターン A を自サーバで実行）
  - 通信の HTTPS 化（パターン B の場合）
  - ログへの PDF 内容出力禁止
  - 変換済みファイルの保持期間ポリシー

---

## 9. Cursor プロジェクトへの引き継ぎプロンプト（コピペ用）

以下を科研費AIシステムの Cursor プロジェクトで新規チャットの冒頭に貼り付けてください。

---

```
【連携元システムの概要】

HUS が運用する「学振PDF読み取り変換Web」があり、学振（IOWebDOC）出力 PDF を
AI 読み取り可能な二層 PDF（背景ラスター + 不可視 Unicode テキスト層）に変換する。

- リポジトリ: https://github.com/keisukekonn-netizen/hus-pdf-converter
- コア: converter.py の convert_jsps_pdf(input_path) → (output_path, stats)
- 依存: pymupdf>=1.24.0
- 背景 216 DPI、テキスト層は render_mode=3（不可視）
- OCR ではなく PyMuPDF get_text("dict") によるテキスト再埋め込み

【やりたいこと】

科研費AIシステムに PDF アップロード機能がある。
学振 PDF をそのまま読むと失敗するため、上記変換をパイプラインに組み込みたい。

【連携方針の候補】

1. converter.py を直接 import してアップロード時に自動変換（推奨）
2. FastAPI 等で /convert API を立てて HTTP 連携
3. テキストのみ必要なら get_text("dict") 結果を JSON で AI に渡す

【制約】

- 申請書は機微情報。処理場所・ログ・保持期間に注意
- 画像のみの PDF は chars=0 となり変換不可
- 変換後 PDF は元よりファイルサイズが大きい

詳細仕様は HANDOVER_科研費AI連携.md を参照。
```

---

## 10. 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-09-01 | 初版作成。背景解像度 300 DPI 対応済み（コミット 94a2f04） |
| 2026-09-01 | 従来は render_scale=2.0（144 DPI）だったが 300 DPI に引き上げ済み |
| 2026-09-01 | ファイルサイズ考慮のため 216 DPI に変更 |
