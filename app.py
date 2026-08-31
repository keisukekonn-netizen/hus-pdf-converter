# -*- coding: utf-8 -*-
"""Hugging Face Spaces / local Gradio app for JSPS PDF conversion."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import gradio as gr

from converter import convert_jsps_pdf, find_japanese_font

ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "").strip()
MAX_PAGES_HINT = "目安: 基盤研究の計画調書（十数頁程度）"


def _status_md(stats: dict, out_name: str) -> str:
    return (
        f"### 変換完了\n\n"
        f"- 出力: `{out_name}`\n"
        f"- ページ数: **{stats['pages']}**\n"
        f"- 埋め込み文字数: **{stats['chars']}**\n"
        f"- テキストありページ: **{stats['pages_with_text']}**\n"
        f"- 使用フォント: `{stats['font']}`\n\n"
        f"ダウンロードしたPDFは、Cursor などでもテキストとして読み取れます。"
    )


def convert_upload(pdf_file, password: str):
    if pdf_file is None:
        raise gr.Error("PDFをアップロードしてください。")

    if ACCESS_PASSWORD:
        if (password or "").strip() != ACCESS_PASSWORD:
            raise gr.Error("パスワードが違います。")

    src_path = Path(pdf_file if isinstance(pdf_file, str) else pdf_file.name)
    if src_path.suffix.lower() != ".pdf":
        raise gr.Error("PDFファイルのみ対応しています。")

    work_dir = Path(tempfile.mkdtemp(prefix="jsps_upload_"))
    try:
        local_in = work_dir / src_path.name
        shutil.copy2(src_path, local_in)
        out_name = f"{local_in.stem}_readable.pdf"
        local_out = work_dir / out_name
        _, stats = convert_jsps_pdf(local_in, local_out)

        # Copy result out of work_dir so Gradio can serve it after cleanup.
        final_dir = Path(tempfile.mkdtemp(prefix="jsps_out_"))
        final_path = final_dir / out_name
        shutil.copy2(local_out, final_path)
        return str(final_path), _status_md(stats, out_name)
    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(f"変換に失敗しました: {e}") from e
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def build_ui() -> gr.Blocks:
    font = find_japanese_font()
    password_note = (
        "共有パスワードが設定されています。案内されたパスワードを入力してください。"
        if ACCESS_PASSWORD
        else "（公開モード: パスワード未設定）"
    )

    with gr.Blocks(title="学振PDF読み取り変換Web") as demo:
        gr.Markdown(
            f"""
# 学振PDF読み取り変換Web

学振（科研費電子申請）から出力したPDFを、**テキストとして読み取れるPDF**に変換します。

- 見た目（帳票レイアウト）はそのまま
- 背面に Unicode テキスト層を付与（Cursor / 検索 / コピー向け）
- アップロードファイルは変換後にサーバ上から削除します
- {MAX_PAGES_HINT}
- 日本語フォント: `{font or "未検出（環境により文字埋め込みが弱い場合あり）"}`
- {password_note}
"""
        )

        with gr.Row():
            pdf_in = gr.File(label="学振PDFをアップロード", file_types=[".pdf"], type="filepath")
            password = gr.Textbox(
                label="共有パスワード",
                type="password",
                visible=bool(ACCESS_PASSWORD),
                placeholder="案内されたパスワード",
            )

        btn = gr.Button("変換する", variant="primary")
        pdf_out = gr.File(label="変換後PDF（ダウンロード）")
        status = gr.Markdown()

        btn.click(fn=convert_upload, inputs=[pdf_in, password], outputs=[pdf_out, status])

        gr.Markdown(
            """
---
### 研究者の方へ
1. このページに学振出力PDFをアップロードする  
2. 「変換する」を押す  
3. ダウンロードした `*_readable.pdf` を利用する  

※ 申請内容は機微情報です。信頼できる運用者から共有されたURLのみ利用してください。
"""
        )
    return demo


demo = build_ui()

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
