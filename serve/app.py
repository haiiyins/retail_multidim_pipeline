"""Demo v0 (Hugging Face Space, Gradio): upload a purchase CSV → top-K models per member with the reason of each recommendation."""
import os, tempfile
import gradio as gr
import pandas as pd

from recommend import load_refs, recommend, validate

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "reference")
REFS = load_refs(REF)
SAMPLE = os.path.join(REF, "sample_purchases.csv")
ABOUT = open(os.path.join(HERE, "ABOUT.md"), encoding="utf-8").read() if os.path.exists(os.path.join(HERE, "ABOUT.md")) else ""


def run(file, k):
    path = file if isinstance(file, str) else (file.name if file is not None else SAMPLE)
    df, rejected = validate(pd.read_csv(path))
    out = recommend(df, REFS, int(k))
    note = (f"{df['member_id'].nunique()} khách, {len(df)} dòng hợp lệ, {rejected} dòng bị loại. "
            f"Dữ liệu tham chiếu tại {next(iter(REFS.values())).asof}. Quốc gia hỗ trợ: {', '.join(REFS)}.")
    csv = os.path.join(tempfile.mkdtemp(), "recommendations.csv")
    out.to_csv(csv, index=False)
    return note, out, csv


with gr.Blocks(title="Next-basket recommendation demo v0") as demo:
    gr.Markdown("# Gợi ý sản phẩm cho kỳ mua tiếp theo — demo v0\n"
                "Tải lên CSV lịch sử mua (`member_id, country_code, model_id, purchase_date, quantity`) hoặc dùng file mẫu "
                "(khách tổng hợp). Mỗi gợi ý kèm nguồn và lý do. Mã sản phẩm và ngành hàng đã được ẩn danh.")
    with gr.Row():
        f = gr.File(label="CSV lịch sử mua (bỏ trống = file mẫu)", file_types=[".csv"])
        k = gr.Slider(5, 30, value=10, step=1, label="Top-K")
    btn = gr.Button("Gợi ý", variant="primary")
    note = gr.Markdown()
    table = gr.Dataframe(wrap=True)
    dl = gr.File(label="Tải kết quả CSV")
    gr.File(value=SAMPLE, label="File mẫu")
    btn.click(run, [f, k], [note, table, dl])
    if ABOUT:
        with gr.Accordion("Về mô hình và kết quả offline", open=False):
            gr.Markdown(ABOUT)

if __name__ == "__main__":
    demo.launch()
