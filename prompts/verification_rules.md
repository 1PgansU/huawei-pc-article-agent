# 华为PC营销软文智能体 — 核验规则集（Verification Rules）

> 目标：在交付前完成 事实 / 图片 / 合规 三道核验拦截
> 输入：DraftArticle + EvidenceMap + ImagePlan
> 输出：VerificationReport（pass/issues/unconfirmed）
> 与提示词（`prompts/system_prompt.md` 模块七、模块八）配套

---

## 1. 总体流程

```python
def verify(draft, evidence_map, image_plan):
    report = {
        "fact_check": run_fact_checks(draft, evidence_map),
        "image_check": run_image_checks(draft, image_plan),
        "compliance_check": run_compliance_checks(draft),
        "unconfirmed": []
    }
    report["overall_pass"] = all([
        report["fact_check"]["pass"],
        report["image_check"]["pass"],
        report["compliance_check"]["pass"]
    ])
    return report
```

---

## 2. 事实核验规则（Fact Check）

### 2.1 型号身份核验

```yaml
rules:
  - id: F01
    name: 型号身份完整
    check: |
      draft 中每个出现的型号名称必须能在 evidence_map.facts 中找到对应条目
      （如 "MateBook 14 鸿蒙版" 必须对应 P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/）
    fail_action: 删除型号或标 [待确认：需指定具体 SKU]

  - id: F02
    name: 系统路线未混用
    check: |
      HarmonyOS 设备的卖点/参数不得用于 Windows 版本，反之亦然
      （如 HarmonyOS 6 / 麒麟 X90 不可写在酷睿 Ultra Windows版软文）
    fail_action: 删除越界事实

  - id: F03
    name: 版本未串用
    check: |
      标准版/柔光版/防窥版的差异化参数不可相互套用
      （如柔光版 600 nits 峰值不可写到标准版）
    fail_action: 删除或改为"特定版本支持"

  - id: F04
    name: 当前款 vs 历史款未混用
    check: |
      历史款官网参考起价/规格不可写成当前在售款
    fail_action: 删除价格/时效描述

  - id: F05
    name: 数字与 ima 一致
    check: |
      draft 中所有数字（重量、尺寸、续航、亮度、刷新率、接口规格、处理器型号、存储容量）
      必须能在 evidence_map.facts 中找到对应来源
    fail_action: 删除数字或标 [待确认：ima 中无依据]

  - id: F06
    name: 商用品价格透明
    check: |
      商用机型若无公开金额，必须写"需官方询价"，不可用相近型号或第三方平台价代填
    fail_action: 改为"需官方询价"

  - id: F07
    name: 用户提供数字核验
    check: |
      用户在任务输入中提供的数字（价格/补贴/库存），若无 ima 依据，
      不得直接写入正文，需在 unconfirmed 块提示用户确认
    fail_action: 移到 unconfirmed，不写入正文
```

### 2.2 数字字段精度要求

```yaml
numeric_field_precision:
  weight: "1.32 kg / 1.33 kg（按方键盘/圆键盘版本区分）"
  thickness: "14.5 mm"
  screen: "14.2 英寸 3:2"
  resolution: "2880 × 1920，243 PPI"
  refresh_rate: "60 Hz / 120 Hz 静态，默认智能动态调节"
  brightness: "标准版 450 nits 典型 / 500 nits 峰值；柔光版 500 / 600 nits"
  battery: "70 Wh（额定容量）"
  ports: "HDMI 2.1 TMDS × 1；USB-A × 2；USB-C × 1；3.5 mm × 1"
  memory: "24 GB / 32 GB"
  storage: "512 GB / 1 TB"
  注意: "数字必须从 P1-产品参数库 对应型号的 产品事实.md 中读取，禁止自由补充"
```

### 2.3 引用格式检查

```yaml
citation_format:
  required:
    - "每条事实后必须附 [来源：本地路径] 或 [来源：官方URL，核验日期]"
    - "动态字段必须写渠道/SKU/地区/核验日期"
    - "图片必须输出 文件名、来源、插入位置、说明"
  fail_action: 自动补充引用，否则标 [待确认]
```

---

## 3. 图片核验规则（Image Check）

### 3.1 三必做检查

```yaml
rules:
  - id: I01
    name: 图片文件名在 ima 图片索引中存在
    check: |
      image_plan 中每个 image.filename 必须在 ima 知识库的
      P1-产品参数库/<型号目录>/图片索引.csv 或 P6-营销素材库/04-图片/ 中可定位
    fail_action: 删除该图片或替换为合规图片

  - id: I02
    name: 图片画面中的产品型号与软文目标型号一致
    check: |
      例如：软文目标型号 = "HUAWEI MateBook 14 鸿蒙版"
      图片画面必须来自该型号目录，禁止从其他型号目录借图
      （如写 MateBook 14 鸿蒙版，配图不能是 MateBook D 14 或 MateBook GT 14）
    fail_action: 替换图片

  - id: I03
    name: 图片画面主题与段落描述一致
    check: |
      例如：段落讲"接口丰富"，配图必须是接口特写图；
      段落讲"屏幕护眼"，配图必须是屏幕图；
      不可用"通用外观图"代替特定功能描述
    fail_action: 重新选图或重写段落
```

### 3.2 图片输出格式检查

```yaml
required_fields_per_image:
  - filename      # 必填，含本地相对路径
  - source_url    # 必填，官方页 URL
  - insert_position  # 必填，开头/中段/结尾/特定段后
  - caption       # 必填，一句话说明为什么这张图放在这里

forbidden:
  - 同一张图在软文中重复使用超过 1 次
  - 图注扩展成图片无法证明的功能
  - 拉伸/裁剪导致型号 logo 失真
  - 使用 ima 之外的网图
```

### 3.3 图片数量校验

```yaml
image_count_check:
  wechat_mp: { min: 2, max: 4 }
  xhs: { min: 3, max: 6 }
  moments: { min: 1, max: 3 }
  poster: { min: 1, max: 1 }
  zhihu: { min: 0, max: 3 }
  short_video: { min: 0, max: 5 }

violation_action:
  too_few: "补充合规图片，否则返回策略层重新生成 ContentPlan"
  too_many: "裁剪多余图片，保留与切角最相关的"
```

---

## 4. 合规核验规则（Compliance Check）

### 4.1 极限词与广告法红线

```yaml
absolutely_forbidden_words:
  极限词:
    - 最、唯一、第一、首个、独家、首发、顶级、最高、最低
    - 全网最低、销量冠军、王牌、爆款
  承诺词:
    - 根治、彻底解决、保证、100%、零风险、零负担
    - 终身免费、终身保修、永久权益
  虚假词:
    - 虚假用户评价、虚构销量、伪造数据、伪造排名
  诱导词:
    - 错过等N年、最后N天、限时抢购
    - 制造焦虑、限量抢购、库存告急
  贬损词:
    - 任何具体竞品的负面描述（除非 ima 的 P3 板块有同期同维度官方证据）

check_pattern: "正则匹配整篇 draft，若命中任一词 → fail"
fail_action: 删除或改写命中句
```

### 4.2 虚构体验检测

```yaml
fabrication_patterns:
  - 亲测、我用了、我朋友、我家人
  - 用了一周/一月/一年都没问题
  - 同事/同学/朋友都说好
  - 实测数据（未标注授权来源）
  - 第一人称故事、伪造客户评价截图
  - "XXX 都在用" 类不可证说法（除非 ima 有授权案例）

check_method: |
  检测第一人称代词 + 时间描述组合，结合关键动词
  若命中且 evidence_map 中无授权记录 → fail
fail_action: 删除或改为 "可在用户实际场景中验证"
```

### 4.3 动态信息检测

```yaml
dynamic_info_without_evidence:
  价格: 数字 + 元/￥/RMB/优惠/补贴/降价/直降/秒杀
  库存: 现货/最后X台/库存告急/X月X日上线
  销量: 销量X万/卖出X台/X分钟售罄
  赠品: 赠/送/加赠/买一送一
  政策: 国补/以旧换新/教育优惠/企业折扣（无 ima 依据时）

check_method: "关键词 + 时间描述 + 数字"
fail_action: |
  - 若 evidence_map 中有依据 → 加上 "渠道、地区、时间、SKU、条件、入口"
  - 若无依据 → 移到 unconfirmed 块，或在末尾加
    "本文不固化价格/库存/赠品，以发布当日授权渠道为准"
```

### 4.4 服务承诺检测

```yaml
service_commitment_patterns:
  - 全国联保、终身保修、终身免费
  - 无条件退换、绝对兼容、全部兼容
  - 任何设备都能接、所有打印机都兼容
  - 上门服务（无地区/机型/时间条件）

fail_action: 删除或改为 "服务方式与费用以官方服务页面/检测结果为准"
```

### 4.5 竞品比较检测

```yaml
competitor_comparison_rules:
  required_conditions_for_valid_comparison:
    - 同期（同日期发布的官方页）
    - 同维度（明确比较的字段）
    - 同任务（明确比较的场景）
    - 同证据（ima 的 P3 板块有官方依据）
  forbidden:
    - 用不同价位、不同系统、不同日期的产品拼成"绝对胜负"
    - 把缺失字段解释为对方"不具备"
    - 任何负面形容词（差、烂、不如）描述具体竞品

fail_action: 删除比较或改为条件化陈述
```

### 4.6 强制保留句式

```yaml
required_disclaimers:
  end_of_article: "不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准。"
  dynamic_info: "本文不固化价格、库存、赠品、政策，以发布当日授权渠道为准。"

check_method: "正则匹配末尾必备句式"
fail_action: 自动补充
```

### 4.7 标题-正文-口播一致性

```yaml
consistency_check:
  principle: |
    标题、封面、口播不能比正文作出更强承诺
    若标题用了"最强"，正文也必须有同等的 ima 依据，否则删除标题词
check_method: |
  - 提取标题/封面/口播中所有承诺性形容词
  - 与正文事实做映射
  - 若标题承诺 > 正文证据 → fail
fail_action: 弱化标题或删除承诺
```

---

## 5. unconfirmed 项处理（未确认信息显式标注）

```yaml
unconfirmed_rules:
  定义: "用户输入或策略层生成但 ima 中无依据的关键信息"
  处理:
    - 不得写入正文
    - 在 VerificationReport 中显式列出
    - 在 UI 上以 [待确认：原因] 醒目展示
    - 提示用户手动确认或删除
  示例:
    - 用户在输入中写了"立减500元" → unconfirmed，等待用户确认渠道/时间/SKU
    - 系统生成时引用了某竞品 → unconfirmed，等待用户确认 ima 是否有依据
```

---

## 6. 拦截 vs 通过决策表

```yaml
decision_table:
  pass_conditions:
    - 事实核验全部通过
    - 图片核验全部通过
    - 合规核验全部通过
    - 无 unconfirmed 项
    - 引用格式完整

  conditional_pass:
    - 事实/图片/合规通过，但有 1-2 个 unconfirmed
    - UI 上显式标注，用户可一键接受或修改

  reject:
    - 事实核验失败 → 重新检索 ima
    - 图片核验失败 → 重新选图
    - 合规核验失败 → 改写后重新提交
    - 极限词/广告法红线命中 → 必删
```

---

## 7. 与提示词的对应

| 提示词模块 | 规则集对应 |
|---|---|
| 模块四 知识库约束 | 2.1 型号身份核验 + 2.2 数字字段精度 |
| 模块五 图片规则 | 3.1 三必做检查 + 3.2 输出格式 + 3.3 数量校验 |
| 模块七 核验规则 | 整体（本文件全部） |
| 模块八 合规规则 | 4.1-4.7 合规核验 |

---

## 8. 落地建议

```yaml
implementation:
  language: Python 3.10+
  suggestion:
    - 用 dataclass + pydantic 约束结构
    - 用正则 + 关键词表做合规扫描
    - 用字典查表做事实/图片匹配
    - 输出标准 VerificationReport JSON
    - 接入 LLM 时作为后置过滤器，不让 LLM 直接生成最终稿
  out_of_scope:
    - LLM 选择与调用（由主程序负责）
    - UI 渲染（由前端负责）
    - ima API 调用（由检索层负责）
```