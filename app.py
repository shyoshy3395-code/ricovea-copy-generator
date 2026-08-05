#!/usr/bin/env python3
"""
RicoVea 天猫商品详情页文案生成器
集成千问 API：视觉识别 + AI 文案生成 + 图片生成
"""

import gradio as gr
import json
import os
import base64
import time
import requests
from openai import OpenAI

# ═══════════════════════════════════════════
# 品牌知识库
# ═══════════════════════════════════════════

BRAND = {
    "name": "RicoVea",
    "slogan": "By Me, I Grow. 由我，自在生长",
    "tagline": "穿回自己。RicoVea。",
    "values": "自在·真实·蓬勃",
    "positioning": "中国新锐设计师品牌",
    "mission": "为灵魂独立的都市年轻女性打造自我表达的精神衣橱",
    "design": "简约·趣味·自在·真实——日常与非常之间的平衡",
    "voice": "有态度不尖锐 / 有审美自信不傲慢 / 利落有节奏感",
    "price_range": "199-3580 RMB，主力区间 489-1880 RMB",
    "audience": "都市独立年轻女性（22-35岁，一线/新一线），独立审美、不被定义、与社交深度绑定",
}

STYLE_QUADRANTS = {
    "时尚职场": {"scene": "办公室、会议、商务社交", "keywords": "利落、结构感、低调有力量", "mood": "专业但不刻板"},
    "日常松弛": {"scene": "咖啡馆、周末、独处", "keywords": "自在、柔软、呼吸感", "mood": "松弛但不随意"},
    "街头休闲": {"scene": "城市漫游、出行、社交", "keywords": "轻松、有型、动态感", "mood": "随性但有态度"},
    "甜酷平衡": {"scene": "约会、派对、创意场合", "keywords": "女性化与硬朗碰撞", "mood": "甜而不腻，酷而不冷"},
    "户外露营": {"scene": "露营、徒步、自然", "keywords": "自在、松弛、与自然共处", "mood": "野而不糙，舒而有型"},
    "闺蜜聚会": {"scene": "下午茶、聚餐、闺蜜时光", "keywords": "精致、轻松、分享感", "mood": "亲密但不随意，精致但不刻意"},
}

SCENE_KEYWORDS = [
    "日常通勤", "甜酷平衡", "休闲街头", "周末松弛",
    "约会派对", "独处时光", "城市漫游",
    "创意场合", "出行社交", "晚间微醺",
    "户外露营", "闺蜜聚会",
]

BANNED_WORDS = ["高级", "优雅", "完美", "绝美", "yyds", "绝绝子", "爆款", "网红"]

# ═══════════════════════════════════════════
# 竞品详情页知识库（AVVENN / ROLAROLA / MOLYCHO）
# ═══════════════════════════════════════════

DETAIL_PAGE_KB = {
    "AVVENN": {
        "structure": "三屏结构：INTRO单品介绍 → 品牌宣言 THE ART OF BALANCE → 洗护说明",
        "selling_format": "5行名词短语（每行≤12字），格式：品类定义 + 设计点×3 + 上身效果 + 穿着场景",
        "example": "多口袋工装裤 → 高腰设计配同色腰带 → 双侧立体大口袋实用有型 → 八分阔腿剪裁卷边露踝 → 显高利落包容身形 → 通勤休闲皆宜",
        "brand_manifesto": "品牌宣言独立一屏，自创品牌概念词（平衡有术/拓扑学家/和谐自治），拒绝'二选一'叙事",
        "price": "¥1,490（中高端设计师品牌）",
        "title_format": "品类 + 货号（如：工装裤 AK71301641）",
    },
    "ROLAROLA": {
        "structure": "Design Highlights（英文标题）→ 品类定义 → 设计点×2-3 → 品牌元素嵌入 → 搭配/造型提示",
        "selling_format": "完整句（主谓宾），5-6行，语序：品类→设计→功能→搭配",
        "example": "经典条纹面料百褶半裙 → 从腰部到褶裥自然过渡 → 中长设计，适配多种场合 → 可搭配基础T恤、针织衫或正装衬衫",
        "brand_element": "rolarola标志性标签作为亮点嵌入详情页，左右分图（正面+背面/可拆卸部件）",
        "price": "¥60-440（中端少女时装）",
        "title_format": "[张元英同款] + 品牌 + 季节 + 风格词 + 设计特征 + 品类 + 效果词",
        "key_insight": "详情页比预期克制——没有emoji、没有明星照片，就是干净的英文标题+结构化中文功能描述",
    },
    "MOLYCHO": {
        "structure": "「花名」体系驱动，每个系列有中文花名跨品类复用",
        "selling_format": "标题即卖点：品牌名 + 「花名」 + 面料质感 + 设计特征 + 品类 + 版型",
        "example": "MOLYCHO「遛弯神裤」原牛色松紧腰抽绳牛仔裤/宽松直筒阔腿休闲裤",
        "flower_names": ["遛弯神裤（松弛）", "自在呼吸（透气/自由，跨品类）", "自有余地（宽松/从容）", "时髦辣妹（性感/自信）"],
        "trust_building": "尺码表含买家真实身高体重参考数据，92%买家认为尺码标准",
        "price": "¥104-246（中端）",
        "key_insight": "给产品系列取中文花名替代货号——'遛弯神裤'比'牛仔裤 AK71301641'更想让人点进去",
    },
}

# ═══════════════════════════════════════════
# 千问 API 客户端
# ═══════════════════════════════════════════

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com"

def get_client(api_key):
    return OpenAI(api_key=api_key, base_url=f"{DASHSCOPE_BASE}/compatible-mode/v1")


def ai_recognize_product(image_path, api_key):
    """上传产品图 → 千问视觉识别 → 返回产品信息"""
    client = get_client(api_key)
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    prompt = """请仔细观察这件服装产品图片，提取以下信息，用 JSON 格式返回：
{
  "product_name": "产品名称（如：廓形西装外套）",
  "fabric": "面料描述（如：棉麻混纺、垂感面料）",
  "color": "颜色",
  "style": "风格关键词",
  "design_details": "设计细节（如：高腰、花苞廓形、立体口袋）",
  "suggested_match": "推荐搭配（如：修身针织衫）",
  "scene": "适合场景（从以下选择1-2个：日常通勤、甜酷平衡、休闲街头、周末松弛、约会派对、独处时光、城市漫游、创意场合、出行社交、晚间微醺、户外露营、闺蜜聚会）"
}
如果某个字段无法确定，填"未知"。只返回 JSON，不要其他内容。"""
    
    r = client.chat.completions.create(
        model="qwen-vl-plus",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]
        }],
        max_tokens=600,
    )
    
    content = r.choices[0].message.content.strip()
    # Clean markdown code fences if present
    content = content.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "识别失败", "raw": content[:300]}


def ai_generate_copy(name, match_styles, scenes, notes, api_key):
    """千问 LLM 生成4种文案方向"""
    client = get_client(api_key)
    
    scene_str = "、".join(scenes) if isinstance(scenes, list) else scenes
    style_info = ""
    for s in (scenes if isinstance(scenes, list) else []):
        if s in STYLE_QUADRANTS:
            info = STYLE_QUADRANTS[s]
            style_info += f"- {s}：{info['mood']}，{info['keywords']}\n"
    
    prompt = f"""你是 RicoVea（中国新锐设计师品牌）的资深文案。
品牌 Slogan：「By Me, I Grow. 由我，自在生长」
品牌调性：有态度不尖锐、有审美自信不傲慢、利落有节奏感
品牌价值观：自在·真实·蓬勃
禁用词：高级、优雅、完美、绝美、yyds、绝绝子

请为以下产品生成4种文案方向：

产品：{name}
搭配：{match_styles}
场景：{scene_str}
场景风格参考：
{style_info}
补充说明：{notes if notes else '无'}

请严格按以下格式输出4个方向，用「---」分隔：

### 一句话金句型
（输出8条品牌态度金句，每条不超过16字，口语化有记忆点）

---

### 小红书种草体
（一段亲近口语化的种草笔记，150-200字，带入真实穿着感受，带#话题标签）

---

### 电商详情页型
（天猫详情页完整文案。参考以下行业格式：
- AVVENN风格：三屏结构，产品介绍→品牌宣言→洗护建议，卖点用名词短语（每行≤12字）
- ROLAROLA风格：Design Highlights英文标题+结构化中文功能描述+搭配方案内置
- MOLYCHO风格：给产品取一个中文「花名」（如「遛弯神裤」「自在呼吸」），让标题有记忆点
RicoVea的品牌宣言：「By Me, I Grow. 由我，自在生长」+ 「自在·真实·蓬勃」150-200字）

---

### 产品拆解型
（设计细节拆解，产品名配场景适配，100-150字）"""

    r = client.chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.8,
    )
    
    content = r.choices[0].message.content
    parts = content.split("---")
    parts = [p.strip() for p in parts]
    while len(parts) < 4:
        parts.append("")
    return tuple(parts[:4])


def ai_generate_image(prompt_text, api_key):
    """根据产品描述生成搭配图"""
    task = requests.post(
        f"{DASHSCOPE_BASE}/api/v1/services/aigc/text2image/image-synthesis",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        },
        json={
            "model": "wanx2.1-t2i-turbo",
            "input": {
                "prompt": f"服装产品展示图，{prompt_text}，干净背景，自然光，极简高级感，时尚摄影风格"
            },
            "parameters": {"size": "1024*1024", "n": 1},
        },
        timeout=30,
    ).json()
    
    task_id = task.get("output", {}).get("task_id")
    if not task_id:
        return None, f"生成失败: {task.get('message', '未知错误')}"
    
    # 轮询结果
    for _ in range(30):
        time.sleep(2)
        result = requests.get(
            f"{DASHSCOPE_BASE}/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        ).json()
        status = result.get("output", {}).get("task_status")
        if status == "SUCCEEDED":
            url = result["output"]["results"][0]["url"]
            return url, None
        elif status == "FAILED":
            return None, result.get("output", {}).get("message", "生成失败")
    
    return None, "生成超时（60秒未完成）"


# ═══════════════════════════════════════════
# 模板引擎（后备方案）
# ═══════════════════════════════════════════

def gen_oneliners(name, match, scenes, notes):
    scene = scenes[0] if scenes else "日常"
    kw = STYLE_QUADRANTS.get(scene, {}).get("keywords", "自在")
    liners = [
        f"贴身的温柔，活动的自由。",
        f"软到忘记在穿，型到不记得在凹。",
        f"不用刻意，也能进入喜欢的状态。",
        f"一件不用迁就自己的{name}。",
        f"在{scene}里，穿回自己。",
        f"简而不凡，{kw}。",
        f"收得果断，放得从容。",
        f"不费力的在场感。",
    ]
    return "### 一句话金句型\n\n" + "\n".join(f"- {l}" for l in liners)


def gen_xhs(name, match, scenes, notes):
    scene = scenes[0] if scenes else "日常"
    mood = STYLE_QUADRANTS.get(scene, {}).get("mood", "松弛自在")
    tags = " ".join([f"#{s.replace(' ', '')}" for s in scenes[:2]])
    return f"""### 这件{name}，穿了一周不想换 🫧

先说面料——{notes if notes else '摸上去是那种温温软软的手感，但穿上活动的时候完全跟得上。'}

版型是刚好合身但不裹的那种，搭配{match}利落干净，单穿也够松弛。{scene}穿它、周末穿它、临时出门抓一件也是它。

上了身才知道什么叫「{mood}」。不是衣服在穿你，是你在穿衣服。

#RicoVea #{name.replace(' ', '')} #自在穿搭 #设计师品牌 {tags}"""


def gen_detail(name, match, scenes, notes):
    scene_str = "、".join(scenes)
    return f"""### {name}

**灵感**
每一件 RicoVea 单品，都是为灵魂独立的都市女性写下的一个短句。{name}也不例外——它以{scene_str}为背景，为日常衣橱注入不费力的设计感。

{notes if notes else f'面料精选优质材质，在触感与结构之间找到平衡。'}

**搭配建议**
搭配{match}，完成属于你的{scene_str}造型。
无论是通勤路上的利落、咖啡馆里的松弛、还是周末街头的随性——一件对的衣服，让你在任何场景里穿回自己。

**品牌**
RicoVea | 中国新锐设计师品牌
{BRAND['slogan']}

关注 @RicoVea，探索更多自在表达。"""


def gen_product_breakdown(name, match, scenes, notes):
    scene_str = "、".join(scenes)
    return f"""### {name}｜贴身的自在

{notes if notes else f'{name}以利落剪裁承载日常——不繁杂、不刻意。'}搭配{match}，在{scene_str}的场景中自然成立。

设计落点在细节：廓形跟随身体而非束缚身体，面料在触感与挺括之间找到平衡。基础款不基础的秘密，全在看不见的地方。

关注 RicoVea，探索更多自在表达。"""


# ═══════════════════════════════════════════
# 主逻辑
# ═══════════════════════════════════════════

def recognize_image(image, api_key):
    """上传图片识别"""
    if image is None:
        return "", "", [], "", "⚠️ 请先上传产品图片"
    if not api_key.strip():
        return "", "", [], "", "⚠️ 请先填写千问 API Key"
    
    result = ai_recognize_product(image, api_key)
    if "error" in result:
        return "", "", [], "", f"❌ {result.get('error', '识别失败')}：{result.get('raw', '')}"
    
    # 映射场景
    scenes = []
    raw_scene = result.get("scene", "")
    if isinstance(raw_scene, str):
        for kw in SCENE_KEYWORDS:
            if kw in raw_scene:
                scenes.append(kw)
    
    return (
        result.get("product_name", ""),
        result.get("suggested_match", ""),
        scenes if scenes else ["日常通勤"],
        f"面料：{result.get('fabric', '未知')} | 颜色：{result.get('color', '未知')} | {result.get('design_details', '')}",
        "✅ 识别完成，请检查并修改后点击生成"
    )


def generate(name, match_styles, scenes, notes, use_ai, api_key):
    """生成文案"""
    if not name.strip():
        return "⚠️ 请输入产品名称", "", "", ""
    
    # 处理场景
    if isinstance(scenes, list):
        scenes_list = scenes if scenes else ["日常通勤"]
    elif isinstance(scenes, str):
        scenes_list = [s.strip() for s in scenes.split(",") if s.strip()] if scenes else ["日常通勤"]
    else:
        scenes_list = ["日常通勤"]
    
    if use_ai and api_key.strip():
        try:
            return ai_generate_copy(name, match_styles, scenes_list, notes, api_key)
        except Exception as e:
            # AI 失败，回退模板
            pass
    
    # 模板生成
    return (
        gen_oneliners(name, match_styles, scenes_list, notes),
        gen_xhs(name, match_styles, scenes_list, notes),
        gen_detail(name, match_styles, scenes_list, notes),
        gen_product_breakdown(name, match_styles, scenes_list, notes),
    )


def generate_image(product_name, notes, api_key):
    """生成搭配图"""
    if not api_key.strip():
        return None, "⚠️ 请先填写千问 API Key"
    
    prompt = f"{product_name}，" + (notes if notes else "设计感剪裁，简约风格")
    url, error = ai_generate_image(prompt, api_key)
    
    if error:
        return None, f"❌ {error}"
    return url, f"✅ 生成完成\n{url}"


# ═══════════════════════════════════════════
# Gradio UI
# ═══════════════════════════════════════════

CUSTOM_CSS = """
.gradio-container {
    max-width: 960px !important;
    margin: 0 auto !important;
    background: #fff !important;
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "苹方", sans-serif !important;
}
body, .gradio-container, .app { background: #fff !important; }
h1, h2, h3 { color: #1D1D1B !important; font-weight: 400 !important; }
h1 { font-size: 1.6em !important; letter-spacing: 0.05em; }
label { color: #666 !important; font-size: 0.85em !important; }
input, textarea, select {
    border: 1px solid #e0e0e0 !important; border-radius: 4px !important;
    background: #fafafa !important; color: #1D1D1B !important; font-size: 0.95em !important;
}
input:focus, textarea:focus { border-color: #ebd1cc !important; box-shadow: 0 0 0 1px #ebd1cc !important; }
button, .gr-button-primary {
    background: #1D1D1B !important; color: #fff !important; border: none !important;
    border-radius: 4px !important; font-size: 0.95em !important; padding: 8px 24px !important;
}
button:hover { background: #333 !important; }
.gr-row > .gr-column { align-self: flex-start !important; }
.gr-dropdown .wrap { min-height: 40px !important; max-height: 80px !important; overflow-y: auto !important; }
.preview-box {
    background: #fafafa !important; border: 1px solid #e8e8e8 !important;
    border-radius: 6px !important; padding: 20px !important; color: #1D1D1B !important;
    font-size: 0.92em !important; line-height: 1.8 !important; white-space: pre-wrap !important;
    min-height: 150px !important;
}
.footer { text-align: center; color: #999; font-size: 0.75em; margin-top: 24px; }
"""

BRAND_HEADER = """
<div style="text-align: center; padding: 24px 0 8px 0;">
    <h1 style="margin:0;">RicoVea 文案生成器</h1>
    <p style="color:#999; font-size:0.85em; margin:8px 0 0 0;">
        By Me, I Grow. 由我，自在生长
    </p>
</div>
"""

FOOTER = """
<div class="footer">
    RicoVea · 中国新锐设计师品牌 · 为灵魂独立的都市年轻女性打造自我表达的精神衣橱
</div>
"""


def build_ui():
    with gr.Blocks(css=CUSTOM_CSS, title="RicoVea 文案生成器", theme=gr.themes.Soft()) as app:
        gr.HTML(BRAND_HEADER)

        # API Key
        api_key = gr.Textbox(
            label="🔑 千问 API Key（可选，不填则使用模板生成）",
            placeholder="sk-...",
            type="password",
            value=os.environ.get("QIANWEN_API_KEY", "sk-ws-H.ELXLPPP.oekq.MEUCIDrYV-s4XjP4ZEwqtc1WRB8efw-fVwzgWhPtxfmhRhAfAiEA2VXzMxdzqBQGBjpeVtkxxqVMto-rBTMX8adLLX6YjN4"),
        )

        gr.Markdown("---")

        # 上传图片识别区
        gr.Markdown("### 📷 上传产品图自动识别")
        with gr.Row():
            image_input = gr.Image(label="上传产品图片", type="filepath", height=200)
            with gr.Column():
                recognize_btn = gr.Button("🔍 AI 识别产品信息", variant="secondary")
                recognize_status = gr.Textbox(label="识别状态", interactive=False)

        gr.Markdown("---")

        # 产品信息
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 产品信息")
                product_name = gr.Textbox(label="产品名称", placeholder="例如：复古花苞短半裙 / 猫咪短袖T恤", lines=1)
                match_styles = gr.Textbox(label="搭配款式", placeholder="例如：修身针织衫 / 牛仔外套", lines=1)
            with gr.Column():
                gr.Markdown("### 场景与补充")
                scene_selector = gr.Dropdown(label="场景词（可多选）", choices=SCENE_KEYWORDS, multiselect=True, value=["日常通勤"])
                notes = gr.Textbox(label="补充说明", placeholder="面料特点 / 设计细节 / 颜色 / 价格...", lines=3)

        # 生成按钮
        with gr.Row():
            generate_btn = gr.Button("📋 模板生成 4 种方向", variant="primary", size="lg")
            ai_generate_btn = gr.Button("🤖 AI 智能生成 4 种方向", variant="secondary", size="lg")
            clear_btn = gr.Button("清空", variant="secondary")

        # 图片生成
        gr.Markdown("### 🖼️ AI 生成搭配图")
        with gr.Row():
            img_gen_btn = gr.Button("🖼️ 生成产品搭配图", variant="secondary")
            img_output = gr.Image(label="生成的搭配图", height=400)
            img_url = gr.Textbox(label="图片链接", interactive=False, visible=False)

        gr.Markdown("---")

        # 输出区
        gr.Markdown("### 一句话金句型")
        output1 = gr.Textbox(label="", lines=8, elem_classes=["preview-box"])

        gr.Markdown("### 小红书种草体")
        output2 = gr.Textbox(label="", lines=8, elem_classes=["preview-box"])

        gr.Markdown("### 电商详情页型")
        output3 = gr.Textbox(label="", lines=10, elem_classes=["preview-box"])

        gr.Markdown("### 产品拆解型")
        output4 = gr.Textbox(label="", lines=8, elem_classes=["preview-box"])

        # 绑定事件
        recognize_btn.click(
            fn=recognize_image,
            inputs=[image_input, api_key],
            outputs=[product_name, match_styles, scene_selector, notes, recognize_status],
        )

        generate_btn.click(
            fn=lambda n, m, s, t, k: generate(n, m, s, t, False, k),
            inputs=[product_name, match_styles, scene_selector, notes, api_key],
            outputs=[output1, output2, output3, output4],
        )

        ai_generate_btn.click(
            fn=lambda n, m, s, t, k: generate(n, m, s, t, True, k),
            inputs=[product_name, match_styles, scene_selector, notes, api_key],
            outputs=[output1, output2, output3, output4],
        )

        img_gen_btn.click(
            fn=generate_image,
            inputs=[product_name, notes, api_key],
            outputs=[img_output, img_url],
        )

        def clear_all():
            return "", "", [], "", "", "", "", "", None, "", None

        clear_btn.click(
            fn=clear_all,
            inputs=[], outputs=[product_name, match_styles, scene_selector, notes,
                               output1, output2, output3, output4, img_output, img_url, recognize_status],
        )

        gr.HTML(FOOTER)

    return app


if __name__ == "__main__":
    app = build_ui()
    port = int(os.environ.get("PORT", 7860))
    app.launch(server_name="0.0.0.0", server_port=port, share=False)
