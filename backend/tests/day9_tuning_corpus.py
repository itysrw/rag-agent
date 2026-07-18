"""Deterministic, self-authored Day 9 retrieval-tuning corpus.

The corpus and questions are pure Python constants: importing this module does
not read files, use randomness, inspect environment variables, or access the
network.  Each source page contains five short policy paragraphs.  A fixed,
synthetic audit identifier makes the pages unambiguously longer than 800
``o200k_base`` tokens while remaining a single unknown token for the pinned BGE
tokenizer.  This controlled construction lets 300/500/800 produce different
chunk counts without violating BGE's independent 512-token input limit.
"""

from __future__ import annotations

from typing import TypedDict


class TuningQuestion(TypedDict):
    """One fixed query and its only objective retrieval-hit phrase."""

    question: str
    expected_phrase: str


DETERMINISTIC_AUDIT_TOKEN = (
    "AX0001BZAX0002BZAX0003BZAX0004BZAX0005BZAX0006BZAX0007BZAX0008BZ"
    "AX0009BZAX0010BZAX0011BZAX0012BZAX0013BZAX0014BZAX0015BZAX0016BZ"
    "AX0017BZAX0018BZAX0019BZAX0020BZAX0021BZAX0022BZAX0023BZAX0024BZ"
    "AX0025BZAX0026BZAX0027BZAX0028BZAX0029BZAX0030BZAX0031BZAX0032BZ"
    "AX0033BZAX0034BZAX0035BZAX0036BZAX0037BZAX0038BZAX0039BZAX0040BZ"
)
AUDIT_SUFFIX = f" 审计校验码：{DETERMINISTIC_AUDIT_TOKEN}"


CORPUS_PAGES: tuple[tuple[str, ...], ...] = (
    (
        "报销票据必须在每月二十五日前提交给财务组，逾期单据进入下个结算周期。"
        "材料应包含发票、消费明细和负责人确认。" + AUDIT_SUFFIX,
        "电子发票会执行重复校验，同一发票不得用于两张报销单。代他人提交时，"
        "备注栏必须说明委托关系。" + AUDIT_SUFFIX,
        "一线城市住宿标准为每晚五百元，二线城市为三百五十元。超标部分原则上"
        "由员工自行承担。" + AUDIT_SUFFIX,
        "市内交通可以报销公共交通和出租车费用，出租车必须附行程单。私车公用"
        "按批准里程领取补贴。" + AUDIT_SUFFIX,
        "业务招待必须提前申请并写明对象、人数和事由。内部员工聚餐不得占用业务"
        "招待额度。" + AUDIT_SUFFIX,
    ),
    (
        "入职满一年不满十年的员工每年享有五天带薪年假，满十年后按制度增加。"
        "假期余额在每年一月刷新。" + AUDIT_SUFFIX,
        "年假至少提前三个工作日在人事系统申请，直属主管批准后才能休假。未经"
        "批准离岗按考勤制度处理。" + AUDIT_SUFFIX,
        "病假应在返岗后两个工作日内补交二级以上医院证明。无法提前请假时，应在"
        "当天通知直属主管。" + AUDIT_SUFFIX,
        "当年未休年假因工作原因最多结转五天，结转天数应在次年第一季度使用。"
        "逾期余额自动作废。" + AUDIT_SUFFIX,
        "连续休假超过五个工作日需要登记职务代理人，并在离岗前完成工作交接。"
        "代理权限在返岗当天失效。" + AUDIT_SUFFIX,
    ),
    (
        "公司外办公必须通过 VPN 接入内网，首次登录使用域账号和动态口令完成双"
        "因素认证。客户端应保持最新版本。" + AUDIT_SUFFIX,
        "VPN 重启后仍无法连接时联系网络组，服务分机是 6203。提交工单时应附客户端"
        "日志和报错截图。" + AUDIT_SUFFIX,
        "夜间紧急故障可拨打 IT 门户公布的值班手机。境外出差人员应提前申请国际"
        "加速通道。" + AUDIT_SUFFIX,
        "VPN 会话连续三十分钟无操作会自动断开，每个账号同时只允许一个会话在线。"
        "异地并发登录会触发告警。" + AUDIT_SUFFIX,
        "VPN 密码连续输错五次会锁定十五分钟。账号不得转借，外包人员必须申请独立"
        "的限时受控账号。" + AUDIT_SUFFIX,
    ),
    (
        "生产数据库全量备份在每周日凌晨两点执行，增量备份在每天凌晨三点半执行。"
        "策略调整须由数据库组长审批。" + AUDIT_SUFFIX,
        "备份文件加密写入主对象存储，并在异地机房保留同步副本。人工读取备份必须"
        "经过双人复核。" + AUDIT_SUFFIX,
        "普通备份文件保留三十天，超过期限由清理任务自动删除。合规留存数据可以"
        "申请延长保存期限。" + AUDIT_SUFFIX,
        "备份失败后监控系统应在十分钟内告警。连续两次失败会升级为高优先级事件，"
        "值班人员当天提交根因。" + AUDIT_SUFFIX,
        "恢复演练每季度执行一次，覆盖单表恢复、整库恢复和跨机房切换。演练缺陷"
        "必须在下一季度前复验。" + AUDIT_SUFFIX,
    ),
    (
        "访客进入办公区前必须完成访客登记，由内部接待人确认身份并全程陪同。访客"
        "证应在离开园区时交回前台。" + AUDIT_SUFFIX,
        "员工门禁卡仅限本人使用，遗失后应立即在安全平台挂失。补办期间由前台发放"
        "当日临时通行证。" + AUDIT_SUFFIX,
        "机房和档案室属于受限区域，普通办公门禁不能直接进入。临时访问必须提交"
        "指定区域授权申请。" + AUDIT_SUFFIX,
        "携带公司设备离开园区时应出示资产放行单。保安核对设备编号与审批记录后"
        "才能放行。" + AUDIT_SUFFIX,
        "办公区门禁日志保留六个月，仅用于安全调查和合规审计。调阅记录需要安全"
        "负责人批准并记录用途。" + AUDIT_SUFFIX,
    ),
    (
        "普通会议室单次预订最长不得超过两个小时，确需延长时应在无人候补的情况下"
        "重新提交下一时段预订。" + AUDIT_SUFFIX,
        "预订人在会议开始前十五分钟仍未签到，系统会自动释放会议室。释放后的时段"
        "可以由其他员工即时预订。" + AUDIT_SUFFIX,
        "视频会议设备故障应联系行政服务台，不得自行拆卸摄像头或控制器。服务台会"
        "根据会议时间安排优先级。" + AUDIT_SUFFIX,
        "超过十人的外部会议应提前一天登记访客名单，并确认会场消防通道没有被家具"
        "或展示材料占用。" + AUDIT_SUFFIX,
        "会议结束后预订人负责清理白板和桌面，并关闭显示设备。遗留物品由前台保管"
        "七天后按失物流程处理。" + AUDIT_SUFFIX,
    ),
    (
        "单笔超过五万元的采购需要总经理审批，审批完成前不得拆分订单或要求供应商"
        "先行交付。" + AUDIT_SUFFIX,
        "常规采购至少比较三家合格供应商的报价。无法完成比价时，申请人必须提交"
        "单一来源采购说明。" + AUDIT_SUFFIX,
        "新供应商准入需要核验营业执照、收款账户和合规承诺。资料失效后供应商会被"
        "暂停接收新订单。" + AUDIT_SUFFIX,
        "采购合同由法务和业务部门共同审核。合同金额、付款节点和验收条件应与采购"
        "申请保持一致。" + AUDIT_SUFFIX,
        "到货后由申请人与资产管理员共同验收。数量或质量不符时不得在系统中确认"
        "收货，也不得触发付款。" + AUDIT_SUFFIX,
    ),
    (
        "新员工的标准笔记本电脑在入职后三个工作日内发放，特殊配置设备需由部门"
        "负责人提前提交申请。" + AUDIT_SUFFIX,
        "账号开通以人事系统的有效入职记录为准。邮箱和即时通信账号通常在入职当天"
        "自动创建。" + AUDIT_SUFFIX,
        "新员工首次登录必须修改临时密码并绑定动态口令。临时密码在发放后二十四"
        "小时失效。" + AUDIT_SUFFIX,
        "软件安装通过 IT 门户申请，管理员权限只按岗位需要临时授予。未经批准不得"
        "安装来源不明的软件。" + AUDIT_SUFFIX,
        "员工离职时应归还电脑、电源和门禁卡。IT 人员完成数据归档后注销账号并更新"
        "资产状态。" + AUDIT_SUFFIX,
    ),
)


QUESTIONS: tuple[TuningQuestion, ...] = (
    {
        "question": "报销票据最晚什么时候提交给财务组？",
        "expected_phrase": "每月二十五日前",
    },
    {
        "question": "入职满一年的员工每年有几天带薪年假？",
        "expected_phrase": "五天带薪年假",
    },
    {
        "question": "VPN 连不上应该联系哪个团队，分机是多少？",
        "expected_phrase": "服务分机是 6203",
    },
    {
        "question": "生产数据库的全量备份在什么时间执行？",
        "expected_phrase": "每周日凌晨两点",
    },
    {
        "question": "访客进入办公区需要办理什么手续？",
        "expected_phrase": "访客登记",
    },
    {
        "question": "会议室单次预订最长可以订多长时间？",
        "expected_phrase": "最长不得超过两个小时",
    },
    {
        "question": "单笔超过五万元的采购需要谁审批？",
        "expected_phrase": "总经理审批",
    },
    {
        "question": "新员工的笔记本电脑多久内发放？",
        "expected_phrase": "三个工作日内发放",
    },
)


def page_texts() -> tuple[str, ...]:
    """Return the fixed pages with paragraph boundaries preserved."""
    return tuple("\n\n".join(paragraphs) for paragraphs in CORPUS_PAGES)
