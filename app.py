#!/usr/bin/env python3
"""
RicoVea 天猫商品详情页文案生成器
"""

import gradio as gr
import json
import os
import base64
from openai import OpenAI

# ═══════════════════════════════════════════
# 品牌知识库
# ═══════════════════════════════════════════

BRAND = {
    "name": "RicoVea",
    "slogan": "By Me, I Grow. 由我，自在生长",
    "tagline": "穿回自己。RicoVea。",
    "values": "自在·真实·蓬勃",
    "voice": "有态度不尖锐 / 有审美自信不傲慢 / 利落有节奏感",
}

STYLE_QUADRANTS = {
    "时尚职场": {"keywords": "利落、结构感、低调有力量", "mood": "专业但不刻板"},
    "日常松弛": {"keywords": "自在、柔软、呼吸感", "mood": "松弛但不随意"},
    "街头休闲": {"keywords": "轻松、有型、动态感", "mood": "随性但有态度"},
    "甜酷平衡": {"keywords": "女性化与硬朗碰撞", "mood": "甜而不腻，酷而不冷"},
    "户外露营": {"keywords": "自在、松弛、与自然共处", "mood": "野而不糙，舒而有型"},
    "闺蜜聚会": {"keywords": "精致、轻松、分享感", "mood": "亲密但不随意，精致但不刻意"},
}

SCENE_KEYWORDS = [
    "日常通勤", "甜酷平衡", "休闲街头", "周末松弛",
    "约会派对", "独处时光", "城市漫游",
    "创意场合", "出行社交", "晚间微醺",
    "户外露营", "闺蜜聚会",
]

# ═══════════════════════════════════════════
# 千问 API
# ═══════════════════════════════════════════

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com"
API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

def get_client():
    if not API_KEY:
        return None
    return OpenAI(api_key=API_KEY, base_url=f"{DASHSCOPE_BASE}/compatible-mode/v1")


def ai_generate(name, selling_points, scene, api_key_override=None):
    """AI 生成4种文案，每种3个变体"""
    key = api_key_override or API_KEY
    if not key:
        return None
    client = OpenAI(api_key=key, base_url=f"{DASHSCOPE_BASE}/compatible-mode/v1")
    
    style_info = STYLE_QUADRANTS.get(scene, {})
    mood = style_info.get("mood", "自在")
    keywords = style_info.get("keywords", "舒适")
    
    prompt = f"""你是 RicoVea 的品牌内容编辑。RicoVea 是中国新锐设计师品牌，Slogan「By Me, I Grow. 由我，自在生长」，价值观「自在·真实·蓬勃」。

现在为以下产品生成文案：
- 产品名称：{name}
- 产品卖点：{selling_points if selling_points else '基础款单品'}
- 场景风格：{scene}（调性：{mood}，关键词：{keywords}）

请用 JSON 格式返回，包含4个字段：
{{
  "产品标题参考": ["标题1", "标题2", "标题3"],
  "详情页商品解析": ["解析1", "解析2", "解析3"],
  "详情页风格文案": ["文案1", "文案2", "文案3"],
  "小红书种草文案": ["文案1", "文案2", "文案3"]
}}

要求：
- 产品标题参考：每个≤9字，像MOLYCHO的「花名」风格，有记忆点
- 详情页商品解析：每个≤30字，像AVVENN的名词短语风格，讲设计细节
- 详情页风格文案：每个≤30字，像ROLAROLA的Design Highlights完整句风格
- 小红书种草文案：每个≤30字，口语化、有态度、适合社媒传播

只返回JSON，不要其他内容。"""

    r = client.chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
    )
    content = r.choices[0].message.content.strip()
    content = content.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def template_generate(name, selling_points, scene):
    """模板生成（无 API 时的 fallback）"""
    mood = STYLE_QUADRANTS.get(scene, {}).get("mood", "自在")
    kw = STYLE_QUADRANTS.get(scene, {}).get("keywords", "舒适")
    
    return {
        "产品标题参考": [
            f"自在{name[:3]}",
            f"{mood[:2]}·{name[:3]}",
            f"穿回自己·{name[:3]}",
        ],
        "详情页商品解析": [
            f"{selling_points or name}，{kw}。{scene}里的{mood}。",
            f"利落剪裁，{kw}。一件融入日常的{name}。",
            f"{name}以流畅廓形承载{mood}。不费力。",
        ],
        "详情页风格文案": [
            f"{name}——{scene}中的{mood}。为你的日常衣橱注入不费力的设计感。",
            f"我们在{name}中寻找廓形与身体之间更自在的结合。{mood}。",
            f"一件{name}，让你在{scene}里穿回自己。{kw}，自然而然。",
        ],
        "小红书种草文案": [
            f"这件{name}上身才知道什么叫「{mood}」。{scene}穿它准没错。",
            f"居然被一件{name}治好了选择困难。{kw}，不用多想就能出门。",
            f"穿了一周的{name}，{mood}。不是衣服在穿你，是你在穿衣服。",
        ],
    }


def generate(name, selling_points, scene, api_key_override=""):
    if not name.strip():
        empty = {"产品标题参考": [""]*3, "详情页商品解析": [""]*3, "详情页风格文案": [""]*3, "小红书种草文案": [""]*3}
        return format_output(empty)
    
    # Try AI first
    result = ai_generate(name, selling_points, scene, api_key_override)
    if result is None:
        result = template_generate(name, selling_points, scene)
    
    return format_output(result)


def format_output(result):
    """将4x3的结果格式化为4个文本框"""
    def fmt(arr):
        return "\n\n".join(f"{i+1}. {a}" for i, a in enumerate(arr))
    
    return (
        fmt(result.get("产品标题参考", [])),
        fmt(result.get("详情页商品解析", [])),
        fmt(result.get("详情页风格文案", [])),
        fmt(result.get("小红书种草文案", [])),
    )


# ═══════════════════════════════════════════
# Gradio 界面
# ═══════════════════════════════════════════

CUSTOM_CSS = """
.gradio-container {
    max-width: 720px !important;
    margin: 0 auto !important;
    background: #fff !important;
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "苹方", sans-serif !important;
}
body, .gradio-container, .app { background: #fff !important; }
h1, h2, h3 { color: #1D1D1B !important; font-weight: 400 !important; }
label, .label-text { color: #666 !important; font-size: 0.82em !important; font-weight: 400 !important; }
input, textarea, select {
    border: 1px solid #e0e0e0 !important; border-radius: 4px !important;
    background: #fafafa !important; color: #1D1D1B !important; font-size: 0.92em !important;
}
input:focus, textarea:focus { border-color: #ebd1cc !important; outline: none !important; box-shadow: 0 0 0 1px #ebd1cc !important; }
button, .gr-button-primary {
    background: #1D1D1B !important; color: #fff !important; border: none !important;
    border-radius: 4px !important; font-size: 0.92em !important; padding: 8px 28px !important; letter-spacing: 0.05em;
}
button:hover { background: #333 !important; }
.preview-box {
    background: #fafafa !important; border: 1px solid #e8e8e8 !important; border-radius: 6px !important;
    padding: 16px !important; color: #1D1D1B !important; font-size: 0.9em !important;
    line-height: 1.8 !important; white-space: pre-wrap !important; min-height: 120px !important;
}
.footer { text-align: center; color: #999; font-size: 0.7em; margin-top: 16px; }
"""

BRAND_HEADER = """
<div style="text-align: center; padding: 20px 0 4px 0;">
    <h1 style="margin:0;font-size:1.3em;">RicoVea 文案生成器</h1>
    <p style="color:#999; font-size:0.8em; margin:6px 0 0 0;">By Me, I Grow. 由我，自在生长</p>
</div>
"""

FOOTER = """<div class="footer">RicoVea · 中国新锐设计师品牌</div>"""


def build_ui():
    with gr.Blocks(title="RicoVea 文案生成器", theme=gr.themes.Soft()) as app:
        gr.HTML(BRAND_HEADER)

        with gr.Row(equal_height=True):
            with gr.Column(scale=2):
                product_name = gr.Textbox(
                    label="产品名称 *",
                    placeholder="例如：复古花苞短半裙 / 廓形西装外套 / 阔腿工装裤",
                    lines=1,
                )
                selling_points = gr.Textbox(
                    label="产品卖点",
                    placeholder="例如：高腰设计、立体花苞廓形、柔弹亲肤面料...",
                    lines=1,
                )
            with gr.Column(scale=1):
                scene_selector = gr.Dropdown(
                    label="场景风格",
                    choices=SCENE_KEYWORDS,
                    value="日常通勤",
                )

        with gr.Row():
            generate_btn = gr.Button("生成", variant="primary", size="lg")
            clear_btn = gr.Button("清空", variant="secondary")

        gr.Markdown("---")

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 产品标题参考")
                gr.Markdown("*3 种，各 ≤9 字*")
                output_title = gr.Textbox(label="", lines=6, elem_classes=["preview-box"])
            with gr.Column():
                gr.Markdown("### 详情页商品解析")
                gr.Markdown("*3 种，各 ≤30 字*")
                output_parse = gr.Textbox(label="", lines=6, elem_classes=["preview-box"])

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 详情页风格文案")
                gr.Markdown("*3 种，各 ≤30 字*")
                output_style = gr.Textbox(label="", lines=6, elem_classes=["preview-box"])
            with gr.Column():
                gr.Markdown("### 小红书种草文案")
                gr.Markdown("*3 种，各 ≤30 字*")
                output_xhs = gr.Textbox(label="", lines=6, elem_classes=["preview-box"])

        generate_btn.click(
            fn=generate,
            inputs=[product_name, selling_points, scene_selector],
            outputs=[output_title, output_parse, output_style, output_xhs],
        )

        def clear_all():
            return "", "", "日常通勤", "", "", "", ""

        clear_btn.click(
            fn=clear_all,
            inputs=[], outputs=[product_name, selling_points, scene_selector,
                               output_title, output_parse, output_style, output_xhs],
        )

        gr.HTML(FOOTER)

    return app


if __name__ == "__main__":
    app = build_ui()
    port = int(os.environ.get("PORT", 7860))
    app.launch(server_name="0.0.0.0", server_port=port, share=False)
