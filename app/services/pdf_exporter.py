"""法务声明 PDF 导出服务"""

from io import BytesIO
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from datetime import datetime


class PDFExporter:
    """法务声明 PDF 导出器"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """设置自定义样式"""
        # 标题样式
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=20
        ))

        # 副标题样式
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=20
        ))

        # 章节标题样式
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            leading=14,
            spaceBefore=12,
            spaceAfter=6
        ))

        # 内容样式
        self.styles.add(ParagraphStyle(
            name='Content',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            spaceBefore=6,
            spaceAfter=6
        ))

    def generate_pdf(
        self,
        declaration_data: dict,
        component_name: str,
        component_version: str,
        system_name: str,
        approval_timeline: list = None
    ) -> bytes:
        """生成法务声明 PDF

        Args:
            declaration_data: 声明表单数据
            component_name: 组件名称
            component_version: 组件版本
            system_name: 系统名称
            approval_timeline: 审批时间线

        Returns:
            PDF 文件的二进制数据
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        elements = []

        # 标题
        elements.append(Paragraph("开源组件法务声明书", self.styles['CustomTitle']))
        elements.append(Paragraph(f"系统：{system_name}", self.styles['Subtitle']))
        elements.append(Paragraph(f"组件：{component_name} v{component_version}", self.styles['Subtitle']))
        elements.append(Spacer(1, 0.5*cm))

        # 声明表单表格
        elements.append(Paragraph("声明信息", self.styles['SectionTitle']))

        form_data = [
            ["使用目的", declaration_data.get('purpose_of_use', '')],
            ["许可证名称", declaration_data.get('license_name', '')],
            ["是否修改", "是" if declaration_data.get('is_modified') == 'yes' else "否"],
            ["使用方式", self._translate_usage_type(declaration_data.get('usage_type', ''))],
            ["源代码 URL", declaration_data.get('url_to_source', '')],
            ["许可证说明 URL", declaration_data.get('license_info_url', '')],
            ["许可证全文 URL", declaration_data.get('license_text_url', '')],
        ]

        form_table = Table(form_data, colWidths=[4*cm, 10*cm])
        form_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(form_table)
        elements.append(Spacer(1, 0.3*cm))

        # 审批时间线
        if approval_timeline:
            elements.append(Paragraph("审批记录", self.styles['SectionTitle']))

            timeline_data = [["审批阶段", "审批人", "审批时间", "状态"]]

            for entry in approval_timeline:
                timeline_data.append([
                    entry.get('stage_name', ''),
                    entry.get('approver_email') or '—',
                    self._format_datetime(entry.get('approved_at')) if entry.get('approved_at') else '—',
                    '✓ 已通过' if entry.get('status') == 'approved' else '○ 待审批'
                ])

            timeline_table = Table(timeline_data, colWidths=[4*cm, 5*cm, 3.5*cm, 2.5*cm])
            timeline_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            elements.append(timeline_table)
            elements.append(Spacer(1, 0.3*cm))

        # 页脚
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(
            f"<i>生成时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>",
            self.styles['Content']
        ))

        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()

        return pdf_data

    def _translate_usage_type(self, usage_type: str) -> str:
        """翻译使用方式"""
        translations = {
            'standalone': '独立可执行程序',
            'dynamically_linked': '动态链接库',
            'statically_linked': '静态链接库',
            'browser_code': '浏览器代码',
            'other': '其他'
        }
        return translations.get(usage_type, usage_type)

    def _format_datetime(self, dt: datetime) -> str:
        """格式化日期时间"""
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M')
        return str(dt) if dt else '—'


def get_pdf_exporter() -> PDFExporter:
    """获取 PDF 导出器实例"""
    return PDFExporter()
