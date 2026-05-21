"""
PDF 合规报告生成器：使用 reportlab 生成专业的中文 PDF 合规审查报告。
"""

import os
import json
from io import BytesIO
from datetime import datetime
from typing import Optional, Dict, List, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ── 注册中文字体 ──────────────────────────────────────────
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

# ── 颜色常量 ──────────────────────────────────────────────
COLOR_PRIMARY = HexColor("#061b31")
COLOR_ACCENT = HexColor("#533afd")
COLOR_GRAY = HexColor("#64748d")
COLOR_LIGHT_GRAY = HexColor("#e5edf5")
COLOR_BG_GRAY = HexColor("#f8fafc")

COLOR_HIGH = HexColor("#ef4444")
COLOR_MEDIUM = HexColor("#f59e0b")
COLOR_LOW = HexColor("#15be53")


# ── 段落样式 ──────────────────────────────────────────────
def _make_styles() -> Dict[str, ParagraphStyle]:
    """创建所有 PDF 段落样式。"""
    font = "STSong-Light"
    return {
        "title": ParagraphStyle(
            "Title",
            fontName=font,
            fontSize=22,
            leading=30,
            alignment=TA_CENTER,
            textColor=COLOR_PRIMARY,
            spaceAfter=6 * mm,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName=font,
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=COLOR_GRAY,
            spaceAfter=10 * mm,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontName=font,
            fontSize=14,
            leading=20,
            textColor=COLOR_PRIMARY,
            spaceBefore=8 * mm,
            spaceAfter=4 * mm,
        ),
        "h3": ParagraphStyle(
            "H3",
            fontName=font,
            fontSize=12,
            leading=18,
            textColor=COLOR_PRIMARY,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=font,
            fontSize=10,
            leading=16,
            textColor=COLOR_GRAY,
            spaceAfter=2 * mm,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            fontName=font,
            fontSize=10,
            leading=16,
            textColor=COLOR_PRIMARY,
            spaceAfter=2 * mm,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontName=font,
            fontSize=8,
            leading=12,
            alignment=TA_CENTER,
            textColor=COLOR_GRAY,
        ),
        "severity_high": ParagraphStyle(
            "SevHigh",
            fontName=font,
            fontSize=10,
            leading=14,
            textColor=COLOR_HIGH,
        ),
        "severity_medium": ParagraphStyle(
            "SevMedium",
            fontName=font,
            fontSize=10,
            leading=14,
            textColor=COLOR_MEDIUM,
        ),
        "severity_low": ParagraphStyle(
            "SevLow",
            fontName=font,
            fontSize=10,
            leading=14,
            textColor=COLOR_LOW,
        ),
        "suggestion": ParagraphStyle(
            "Suggestion",
            fontName=font,
            fontSize=10,
            leading=16,
            textColor=HexColor("#273951"),
            leftIndent=8 * mm,
            spaceAfter=2 * mm,
        ),
    }


def _severity_color(severity: str) -> HexColor:
    """根据严重程度返回颜色。"""
    mapping = {
        "high": COLOR_HIGH,
        "medium": COLOR_MEDIUM,
        "low": COLOR_LOW,
    }
    return mapping.get(severity, COLOR_GRAY)


def _severity_label(severity: str) -> str:
    """严重程度中文标签。"""
    mapping = {
        "high": "高风险",
        "medium": "中风险",
        "low": "低风险",
    }
    return mapping.get(severity, "未知")


def _score_color(score: int) -> HexColor:
    """根据分数返回颜色。"""
    if score >= 70:
        return COLOR_HIGH
    if score >= 40:
        return COLOR_MEDIUM
    return COLOR_LOW


def _score_label(score: int) -> str:
    """根据分数返回标签。"""
    if score >= 70:
        return "高风险"
    if score >= 40:
        return "中风险"
    return "低风险"


# ── 主生成函数 ────────────────────────────────────────────
def generate_pdf_report(
    review_data: Dict[str, Any],
    filename: Optional[str] = None,
) -> bytes:
    """
    生成 PDF 合规审查报告并返回字节流。

    Args:
        review_data: 审查结果字典（与 ReviewResult 对应）
        filename: 原始上传文件名（可选）

    Returns:
        PDF 文件的 bytes 内容
    """
    buf = BytesIO()
    styles = _make_styles()
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    def _footer(canvas, doc):
        """页脚回调。"""
        canvas.saveState()
        canvas.setFont("STSong-Light", 8)
        canvas.setFillColor(COLOR_GRAY)
        page_num = canvas.getPageNumber()
        text = f"合同合规审查报告 | 第 {page_num} 页 | 生成时间: {timestamp_str}"
        canvas.drawCentredString(A4[0] / 2, 12 * mm, text)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    elements: List[Any] = []

    # ── 标题 ────────────────────────────────────────────
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph("合同合规审查报告", styles["title"]))
    elements.append(
        Paragraph(
            "ContractAI - 智能合同合规审查工具",
            styles["subtitle"],
        )
    )
    elements.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY))
    elements.append(Spacer(1, 4 * mm))

    # ── 1. 基本信息 ────────────────────────────────────
    elements.append(Paragraph("一、基本信息", styles["h2"]))

    contract_type = review_data.get("contract_type", "未知")
    file_id = review_data.get("file_id", "-")
    review_time = review_data.get("review_time", timestamp_str)
    original_name = filename or file_id

    info_data = [
        ["合同类型", contract_type],
        ["文件名称", original_name],
        ["文件标识", file_id],
        ["审查时间", review_time if review_time else timestamp_str],
    ]
    info_table = Table(info_data, colWidths=[40 * mm, 120 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), COLOR_PRIMARY),
                ("TEXTCOLOR", (1, 0), (1, -1), COLOR_GRAY),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, COLOR_LIGHT_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(info_table)
    elements.append(Spacer(1, 4 * mm))

    # ── 2. 风险评分概要 ────────────────────────────────
    elements.append(Paragraph("二、风险评分概要", styles["h2"]))

    risk_score = review_data.get("risk_score", 0)
    risk_level = review_data.get("risk_level", "low")
    score_color = _score_color(risk_score)
    score_label = _score_label(risk_score)

    # 评分显示表格
    score_display = [
        [
            Paragraph(f"<b>风险评分: {risk_score} 分</b>", styles["body_bold"]),
            Paragraph(f"<b>{score_label}</b>", styles["body_bold"]),
        ]
    ]
    score_table = Table(score_display, colWidths=[80 * mm, 80 * mm])
    score_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (0, 0), COLOR_BG_GRAY),
                ("TEXTCOLOR", (0, 0), (0, 0), score_color),
                ("TEXTCOLOR", (1, 0), (1, 0), score_color),
                ("BACKGROUND", (1, 0), (1, 0), COLOR_BG_GRAY),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_LIGHT_GRAY),
            ]
        )
    )
    elements.append(score_table)

    # 风险等级条
    bar_width = (risk_score / 100.0) * 160 * mm
    bar_data = [[""]]
    bar_table = Table(bar_data, colWidths=[bar_width, 160 * mm - bar_width])
    bar_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), score_color),
                ("BACKGROUND", (1, 0), (1, 0), COLOR_LIGHT_GRAY),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -1), 0, white),
                ("LINEABOVE", (0, 0), (-1, -1), 0, white),
            ]
        )
    )
    elements.append(Spacer(1, 2 * mm))
    elements.append(bar_table)

    # 统计
    issues = review_data.get("issues", [])
    high_count = sum(1 for i in issues if i.get("severity") == "high")
    medium_count = sum(1 for i in issues if i.get("severity") == "medium")
    low_count = sum(1 for i in issues if i.get("severity") == "low")

    stat_text = (
        f"共发现 {len(issues)} 个风险问题："
        f"高风险 {high_count} 项、中风险 {medium_count} 项、低风险 {low_count} 项"
    )
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(stat_text, styles["body"]))
    elements.append(Spacer(1, 4 * mm))

    # ── 3. 合规分析摘要 ────────────────────────────────
    elements.append(Paragraph("三、合规分析摘要", styles["h2"]))
    summary = review_data.get("summary", "暂无摘要")
    elements.append(Paragraph(summary, styles["body"]))
    elements.append(Spacer(1, 4 * mm))

    # ── 4. 风险问题详情 ────────────────────────────────
    elements.append(Paragraph("四、风险问题详情", styles["h2"]))

    if not issues:
        elements.append(Paragraph("未发现风险问题。", styles["body"]))
    else:
        for idx, issue in enumerate(issues, start=1):
            title = issue.get("clause", issue.get("title", f"问题 {idx}"))
            severity = issue.get("severity", "low")
            description = issue.get("description", "")
            suggestion = issue.get("suggestion", "")
            risk_type = issue.get("risk_type", "")

            sev_color = _severity_color(severity)
            sev_label = _severity_label(severity)

            # 问题标题行
            header_data = [
                [
                    Paragraph(
                        f"<b>{idx}. {title}</b>",
                        styles["body_bold"],
                    ),
                    Paragraph(
                        f"<b>{sev_label}</b>",
                        ParagraphStyle(
                            f"sev_{idx}",
                            fontName="STSong-Light",
                            fontSize=10,
                            leading=14,
                            textColor=sev_color,
                            alignment=TA_RIGHT,
                        ),
                    ),
                ]
            ]
            header_table = Table(header_data, colWidths=[140 * mm, 20 * mm])
            header_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            elements.append(header_table)

            # 风险类型标签
            if risk_type:
                elements.append(
                    Paragraph(f"风险类型: {risk_type}", styles["body"])
                )

            # 问题描述
            elements.append(Paragraph("问题描述:", styles["body_bold"]))
            elements.append(Paragraph(description, styles["body"]))

            # 修改建议
            elements.append(Paragraph("修改建议:", ParagraphStyle(
                f"sug_label_{idx}",
                fontName="STSong-Light",
                fontSize=10,
                leading=14,
                textColor=COLOR_ACCENT,
                spaceBefore=2 * mm,
            )))
            elements.append(Paragraph(suggestion, styles["suggestion"]))

            # 分隔线
            if idx < len(issues):
                elements.append(HRFlowable(
                    width="100%",
                    thickness=0.3,
                    color=COLOR_LIGHT_GRAY,
                    spaceAfter=4 * mm,
                    spaceBefore=4 * mm,
                ))

    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY))
    elements.append(Spacer(1, 2 * mm))
    elements.append(
        Paragraph(
            f"本报告由 ContractAI 智能合同合规审查工具自动生成 | {timestamp_str}",
            styles["footer"],
        )
    )

    # ── 构建 PDF ───────────────────────────────────────
    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
