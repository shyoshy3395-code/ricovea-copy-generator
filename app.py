#!/usr/bin/env python3
"""
RicoVea 天猫商品详情页文案生成器
"""

import gradio as gr
import json
import os
import base64
from openai import OpenAI

# ═══════════════════════════
# 品牌知识库
# ═══════════════════════════

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

# ═══════════════════════════
# 全品牌参考知识库（8个品牌，覆盖详情页+小红书）
# ═══════════════════════════

ALL_BRANDS_KB = """
【天猫详情页参考品牌】

■ AVVENN（设计师品牌，¥1490）
- 详情页结构：INTRO单品介绍 → 品牌宣言 THE ART OF BALANCE → 洗护说明
- 卖点格式：5行名词短语（每行≤12字），无动词
- 示例：多口袋工装裤 → 高腰设计配同色腰带 → 双侧立体大口袋实用有型 → 八分阔腿剪裁卷边露踝 → 显高利落包容身形 → 通勤休闲皆宜

■ ROLAROLA（少女时装，¥60-440）
- 详情页结构：Design Highlights（英文标题）→ 品类定义+设计特征 → 设计细节展开 → 版型/穿着体验 → 搭配方案 → 收尾评价
- 卖点格式：完整句（主谓宾），5-6行
- 示例：经典条纹面料百褶半裙 → 从腰部到褶裥自然过渡 → 中长设计，适配多种场合 → 可搭配基础T恤、针织衫或正装衬衫

■ MOLYCHO（商业女装，¥104-246）
- 产品命名：「花名」体系驱动，每个系列有中文花名跨品类复用
- 标题格式：品牌名 + 「花名」 + 面料质感 + 设计特征 + 品类 + 版型
- 示例：MOLYCHO「遛弯神裤」原牛色松紧腰抽绳牛仔裤/宽松直筒阔腿休闲裤
- 花名列表：「遛弯神裤」「自在呼吸」「自有余地」「时髦辣妹」

【小红书文案参考品牌】

■ alright then（设计师品牌）
- 核心手法：「就褶样呗」态度系列化——每篇标题统一前缀+场景词
- 句式特征：产品穿着感受 → 场景状态 → 金句收尾（「自在，是______。」）
- 代表金句：「汉麻会皱，生活也是」「自在，是忙而不乱，热而不躁」

■ Short Sentence（设计师品牌）
- 核心手法：产品拆解型——每篇拆解1-3件单品的设计细节
- 句式特征：色彩文学化命名（「勃艮第：像被阳光晒过的深葡萄」）
- 品牌名复用：「短句女孩」「短句式惊喜」

■ AAAD / an action a day（运动休闲）
- 核心手法：栏目化内容体系（編輯/專題/發聲/坐標）
- 句式特征：书信体、排比递进（「允许复杂，允许变化，允许她完整出现」）
- 用户关系命名：「共同行动人」替代「顾客」

■ 有尾 YOUWEI（设计师品牌）
- 核心手法：系列化寓言连载——把订货会变成四幕剧《石头国的石头人》
- 句式特征：连载式结尾（「故事就从这儿开始了......」）
- 统一CTA：「预约通道现已全部开启，静待莅临」

■ hug（买手店）
- 核心手法：栏目前缀建立内容体系（in hug / hug share / hug x）
- 句式特征：策展人式克制文案，文化引用常态化
"""

# ═══════════════════════════
# 千问 API
# ═══════════════════════════

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com"
API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")


def ai_recognize_product(image_path, api_key):
    """上传产品图 → 千问视觉识别 → 返回产品信息"""
    if not api_key:
        return {"error": "请先输入 API Key"}
    client = OpenAI(api_key=api_key, base_url=f"{DASHSCOPE_BASE}/compatible-mode/v1")
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    prompt = """请观察这件服装产品图片，提取以下信息，用 JSON 返回：
{"product_name": "产品名称（如：廓形西装外套）", "selling_points": "产品卖点（面料、设计细节、廓形特征）", "scene": "场景风格（从以下选择1个：日常通勤、甜酷平衡、休闲街头、周末松弛、约会派对、独处时光、城市漫游、创意场合、出行社交、晚间微醺、户外露营、闺蜜聚会）"}
只返回 JSON。"""
    
    r = client.chat.completions.create(
        model="qwen-vl-plus",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
        ]}],
        max_tokens=300,
    )
    content = r.choices[0].message.content.strip()
    content = content.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "识别失败", "raw": content[:200]}


def ai_generate(name, selling_points, scene, api_key):
    """AI 生成4种文案，每种3个变体"""
    if not api_key:
        return None
    client = OpenAI(api_key=api_key, base_url=f"{DASHSCOPE_BASE}/compatible-mode/v1")
    
    style_info = STYLE_QUADRANTS.get(scene, {})
    mood = style_info.get("mood", "自在")
    keywords = style_info.get("keywords", "舒适")
    
    prompt = f"""你是 RicoVea 的品牌内容编辑。RicoVea 是中国新锐设计师品牌，Slogan「By Me, I Grow. 由我，自在生长」，价值观「自在·真实·蓬勃」。

以下是行业竞品参考知识库，请学习并参考其风格：

{ALL_BRANDS_KB}

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
            f"{selling_points or name}，{kw}。{scene}里的{mood[:4]}。",
            f"利落剪裁，{kw}。一件融入日常的{name}。",
            f"{name}以流畅廓形承载{mood[:4]}。不费力。",
        ],
        "详情页风格文案": [
            f"{name}——{scene}中的{mood[:4]}。为日常衣橱注入设计感。",
            f"我们在{name}中寻找廓形与身体之间更自在的结合。",
            f"一件{name}，让你在{scene}里穿回自己。{kw}。",
        ],
        "小红书种草文案": [
            f"这件{name}上身才知道什么叫「{mood[:4]}」。{scene}穿它准没错。",
            f"居然被一件{name}治好了选择困难。{kw}，不用多想就能出门。",
            f"穿了一周的{name}，{mood[:4]}。是你在穿衣服。",
        ],
    }


def generate(name, selling_points, scene, api_key):
    if not name.strip():
        empty = {"产品标题参考": [""]*3, "详情页商品解析": [""]*3, "详情页风格文案": [""]*3, "小红书种草文案": [""]*3}
        return format_output(empty)
    
    result = ai_generate(name, selling_points, scene, api_key)
    if result is None:
        result = template_generate(name, selling_points, scene)
    
    return format_output(result)


def format_output(result):
    def fmt(arr):
        return "\n\n".join(f"{i+1}. {a}" for i, a in enumerate(arr))
    return (
        fmt(result.get("产品标题参考", [])),
        fmt(result.get("详情页商品解析", [])),
        fmt(result.get("详情页风格文案", [])),
        fmt(result.get("小红书种草文案", [])),
    )


# ═══════════════════════════
# Gradio 界面
# ═══════════════════════════

CUSTOM_CSS = """
.gradio-container { max-width: 720px !important; margin: 0 auto !important; background: #fff !important; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "苹方", sans-serif !important; }
body, .gradio-container, .app { background: #fff !important; }
h1, h2, h3 { color: #1D1D1B !important; font-weight: 400 !important; }
label, .label-text { color: #666 !important; font-size: 0.82em !important; font-weight: 400 !important; }
input, textarea, select { border: 1px solid #e0e0e0 !important; border-radius: 4px !important; background: #fafafa !important; color: #1D1D1B !important; font-size: 0.92em !important; }
input:focus, textarea:focus { border-color: #ebd1cc !important; outline: none !important; box-shadow: 0 0 0 1px #ebd1cc !important; }
button, .gr-button-primary { background: #1D1D1B !important; color: #fff !important; border: none !important; border-radius: 4px !important; font-size: 0.92em !important; padding: 8px 28px !important; letter-spacing: 0.05em; }
button:hover { background: #333 !important; }
.preview-box { background: #fafafa !important; border: 1px solid #e8e8e8 !important; border-radius: 6px !important; padding: 16px !important; color: #1D1D1B !important; font-size: 0.9em !important; line-height: 1.8 !important; white-space: pre-wrap !important; min-height: 120px !important; }
.footer { text-align: center; color: #999; font-size: 0.7em; margin-top: 16px; }
.recognize-section { background: #f5f0ff !important; padding: 12px !important; border-radius: 6px !important; margin-bottom: 12px !important; }
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

        # ── 上传产品图自动识别 ──
        with gr.Row():
            with gr.Column():
                product_image = gr.Image(label="上传产品图", type="filepath", height=200)
            with gr.Column():
                gr.Markdown("### 视觉模型 API Key")
                api_key = gr.Textbox(
                    label="DashScope API Key",
                    placeholder="sk-...",
                    type="password",
                )
                recognize_btn = gr.Button("🔍 AI 识别产品信息", variant="secondary")
                recognize_status = gr.Markdown("")

        # ── 产品信息 ──
        gr.Markdown("### 产品信息")
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

        # ── 事件绑定 ──

        def do_recognize(img, key):
            if img is None:
                return "", "", "日常通勤", "⚠️ 请先上传产品图"
            result = ai_recognize_product(img, key)
            if "error" in result:
                return "", "", "日常通勤", f"❌ {result['error']}"
            name = result.get("product_name", "")
            points = result.get("selling_points", "")
            scene = result.get("scene", "日常通勤")
            if scene not in SCENE_KEYWORDS:
                scene = "日常通勤"
            status = f"✅ 识别完成：{name} | {scene}"
            return name, points, scene, status

        recognize_btn.click(
            fn=do_recognize,
            inputs=[product_image, api_key],
            outputs=[product_name, selling_points, scene_selector, recognize_status],
        )

        generate_btn.click(
            fn=generate,
            inputs=[product_name, selling_points, scene_selector, api_key],
            outputs=[output_title, output_parse, output_style, output_xhs],
        )

        def clear_all():
            return None, "", "", "", "日常通勤", "", "", "", "", ""

        clear_btn.click(
            fn=clear_all,
            inputs=[], outputs=[product_image, api_key, product_name, selling_points, scene_selector,
                               output_title, output_parse, output_style, output_xhs, recognize_status],
        )

        gr.HTML(FOOTER)

    return app


if __name__ == "__main__":
    app = build_ui()
    port = int(os.environ.get("PORT", 7860))
    app.launch(server_name="0.0.0.0", server_port=port, share=False)
