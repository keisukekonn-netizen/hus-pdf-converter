# -*- coding: utf-8 -*-
"""Streamlit app: convert Kakenhi PDFs into text-readable PDFs."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import streamlit as st

from converter import convert_jsps_pdf, find_japanese_font


def _access_password() -> str:
    # Streamlit Cloud: Settings → Secrets に ACCESS_PASSWORD = "..."
    try:
        if "ACCESS_PASSWORD" in st.secrets:
            return str(st.secrets["ACCESS_PASSWORD"]).strip()
    except Exception:
        pass
    return os.environ.get("ACCESS_PASSWORD", "").strip()


def main() -> None:
    st.set_page_config(page_title="学振PDF読み取り変換Web", page_icon="📄", layout="centered")
    password_required = _access_password()
    font = find_japanese_font()

    st.caption("北海道科学大学　研究推進社会実装センター")
    st.title("学振PDF読み取り変換Web")
    st.markdown(
        """
学振（科研費電子申請）から出力したPDFを、**テキストとして読み取れるPDF**に変換します。

- 見た目（帳票レイアウト）はそのまま
- 背面に Unicode テキスト層を付与（科研費AIシステム向け）
- アップロードファイルは変換後にサーバ上から削除します
- 目安: 基盤研究の計画調書（十数頁程度）
"""
    )
    st.caption(f"日本語フォント: `{font}`")
    if password_required:
        st.info("共有パスワードが設定されています。案内されたパスワードを入力してください。")
    else:
        st.caption("（公開モード: パスワード未設定）")

    password = ""
    if password_required:
        password = st.text_input("共有パスワード", type="password")

    uploaded = st.file_uploader("学振PDFをアップロード", type=["pdf"])

    if st.button("変換する", type="primary", disabled=uploaded is None):
        if password_required and password.strip() != password_required:
            st.error("パスワードが違います。")
            return
        if uploaded is None:
            st.error("PDFをアップロードしてください。")
            return

        work_dir = Path(tempfile.mkdtemp(prefix="hus_upload_"))
        try:
            with st.spinner("変換中です…"):
                in_path = work_dir / uploaded.name
                in_path.write_bytes(uploaded.getvalue())
                out_name = f"{in_path.stem}_readable.pdf"
                out_path = work_dir / out_name
                _, stats = convert_jsps_pdf(in_path, out_path)
                data = out_path.read_bytes()

            st.success("変換完了")
            st.markdown(
                f"""
- 出力: `{out_name}`
- ページ数: **{stats['pages']}**
- 埋め込み文字数: **{stats['chars']}**
- テキストありページ: **{stats['pages_with_text']}**
- 使用フォント: `{stats['font']}`
"""
            )
            st.download_button(
                label="変換後PDFをダウンロード",
                data=data,
                file_name=out_name,
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"変換に失敗しました: {e}")
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    st.divider()
    st.markdown(
        """
### 研究者の方へ
1. このページに学振出力PDFをアップロードする  
2. 「変換する」を押す  
3. ダウンロードした `*_readable.pdf` を利用する  

※ 申請内容は機微情報です。信頼できる運用者から共有されたURLのみ利用してください。
"""
    )


if __name__ == "__main__":
    main()
