import os
import re
import imaplib
import email
from email.header import decode_header
from datetime import datetime
import logging
import requests
import json
from fpdf import FPDF

# =================================================================================
# === 配置区 (已根据最新信息确认) ===
# =================================================================================
IMAP_URL = 'imap.gmail.com'
EMAIL_USER = 'zoey.yuan@anker.com'
EMAIL_PASS = 'lxau jhmd ylvi ewvj'
VALID_SENDERS = ["Donna.Villani@directed.com.au"]
ATTACHMENT_PATTERN = re.compile(r'^AP Credit Memo.*\.pdf$', re.IGNORECASE)
EMAIL_SENT_DATE = "15-Jul-2025"
BASE_SAVE_DIR = os.path.expanduser('~/Desktop/CN发票下载')  # 使用当前用户目录
FONT_PATH = '/System/Library/Fonts/STHeiti Medium.ttc'
FEISHU_APP_ID = "cli_a702c225665e100d"
FEISHU_APP_SECRET = "5D7PoQaMtb8Er1qqfUnGpfcYiFekaX2b"
FEISHU_PARENT_NODE = "W8v4f46zBlTJkldWPPmcTHqanTh"
FEISHU_BITABLE_APP_TOKEN = "H0MSb4s0vaJ1VXsxq5Kcc9DCnKg"
FEISHU_BITABLE_TABLE_ID = "tbldq9wHDecaWW7B"


# =================================================================================
# === 功能模块 (无需修改) ===
# =================================================================================
def setup_logging(log_base_dir):
    """设置日志记录"""
    log_dir = os.path.join(log_base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}_run_log.txt")
    
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )


class FeishuApplication:
    """飞书应用接口类"""
    
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = self.get_tenant_access_token()
        self.headers = {'Authorization': f'Bearer {self._token}'} if self._token else {}

    def get_tenant_access_token(self):
        """获取租户访问令牌"""
        url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
        try:
            response = requests.post(
                url,
                json={"app_id": self.app_id, "app_secret": self.app_secret}
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == 0:
                logging.info('获取token成功')
                return data['tenant_access_token']
            else:
                logging.error(f'获取token失败：{response.text}')
                return None
        except Exception as e:
            logging.error(f"请求Token出错: {e}")
            return None

    def create_folder(self, name, parent):
        """创建文件夹"""
        if not self._token:
            return None, None
        
        url = 'https://open.feishu.cn/open-apis/drive/v1/files/create_folder'
        try:
            response = requests.post(
                url,
                headers={**self.headers, 'Content-Type': 'application/json'},
                json={"name": name, "folder_token": parent}
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                return data['data']['token'], data['data']['url']
            else:
                logging.error(f'建文件夹失败：{response.text}')
                return None, None
        except Exception as e:
            logging.error(f"建文件夹出错: {e}")
            return None, None

    def upload_file(self, path, parent):
        """上传文件到云空间文件夹（支持wiki空间）"""
        if not self._token or not os.path.isfile(path):
            return None
        
        # 检查是否为wiki空间下的文件夹
        # wiki空间的文件夹token通常以特定前缀开头
        url = 'https://open.feishu.cn/open-apis/drive/v1/files/upload_all'
        
        try:
            name = os.path.basename(path)
            file_size = os.path.getsize(path)
            
            # 构建正确的multipart/form-data格式
            files = {
                'file_name': (None, name),
                'parent_type': (None, 'bitable_file'),  # 对于wiki空间也使用explorer
                'parent_node': (None, FEISHU_BITABLE_APP_TOKEN),       # 父文件夹token
                'size': (None, str(file_size)),      # 文件大小
                'file': (name, open(path, 'rb'), 'application/pdf')
                # 'extra': (None, json.dumps({"drive_route_token":"A8IDwivqLiAovzksBkzcfj3GnCb"}))
            }
            
            # 对于wiki空间，可能需要特殊的headers
            headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
            
            # 添加wiki空间支持的额外参数（如果需要）
            # headers['X-Space-Type'] = 'wiki'  # 根据实际API要求添加
            
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                logging.info(f"文件'{name}'上传成功到wiki空间")
                return data['data']['file_token']
            else:
                logging.error(f"文件'{name}'上传失败：{response.text}")
                # 如果是权限错误，提供详细的错误信息
                if 'AttachPermNotAllow' in response.text:
                    logging.error("权限错误：请确保应用已添加到wiki页面并具有编辑权限")
                return None
                
        except Exception as e:
            logging.error(f"上传文件出错: {e}")
            return None
        finally:
            if 'files' in locals() and 'file' in files:
                try:
                    files['file'][1].close()
                except:
                    pass

    def write_records_to_bitable(self, app_token, table_id, records):
        """写入记录到多维表格"""
        if not self._token:
            logging.error("无法写入：无效Token")
            return False
        
        if not records:
            logging.info("无数据写入")
            return True
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
        payload = {"records": [{"fields": r} for r in records]}  # 修正payload格式
        
        logging.info(f"准备写入多维表格: app_token={app_token}, table_id={table_id}")
        logging.info(f"请求URL: {url}")
        logging.info(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        try:
            response = requests.post(
                url,
                headers={**self.headers, 'Content-Type': 'application/json'},
                json=payload
            )
            
            logging.info(f"响应状态码: {response.status_code}")
            logging.info(f"响应内容: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    logging.info(f"✅ 成功向多维表格写入 {len(records)} 条记录")
                    return True
                else:
                    logging.error(f"❌ API返回错误: {data.get('msg', '未知错误')}")
                    return False
            else:
                logging.error(f"写入HTTP错误: {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"写入异常: {str(e)}")
            return False


def save_text_as_pdf(text, path):
    """将文本保存为PDF"""
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # 改进字体处理
        try:
            if os.path.exists(FONT_PATH):
                pdf.add_font('Heiti', '', FONT_PATH, uni=True)
                pdf.set_font('Heiti', size=12)
            else:
                # 使用内置字体处理英文内容
                pdf.set_font('Arial', size=12)
                # 过滤非ASCII字符
                text = text.encode('ascii', 'ignore').decode('ascii')
        except Exception as font_error:
            logging.warning(f"字体加载失败，使用默认字体: {font_error}")
            pdf.set_font('Arial', size=12)
            text = text.encode('ascii', 'ignore').decode('ascii')
        
        pdf.multi_cell(0, 10, txt=text)
        pdf.output(path)
        return True
    except Exception as e:
        logging.error(f"创建PDF失败: {e}")
        return False


def process_and_upload_emails(feishu_robot, daily_folder_token):
    """处理和上传邮件"""
    records = []
    
    # 创建临时目录
    temp_dir = os.path.join(BASE_SAVE_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 连接邮箱
        mail = imaplib.IMAP4_SSL(IMAP_URL)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('Inbox')
        
        # 遍历有效发件人
        for sender in VALID_SENDERS:
            _, data = mail.search(None, f'(FROM "{sender}" SENTON {EMAIL_SENT_DATE})')
            
            for mail_id in data[0].split():
                try:
                    # 获取邮件内容
                    _, msg_data = mail.fetch(mail_id, '(RFC822)')
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # 解析邮件主题
                    subject, encoding = decode_header(msg['Subject'])[0]
                    subject = subject.decode(encoding or 'utf-8') if isinstance(subject, bytes) else subject
                    
                    # 匹配Credit Memo ID
                    match = re.search(r'Credit Memo_\s*(\d+)', subject, re.IGNORECASE)
                    if not match:
                        continue
                    
                    memo_id = match.group(1)
                    base_name = f"Credit Memo_{memo_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    # 创建ID文件夹
                    id_folder_token, _ = feishu_robot.create_folder(memo_id, daily_folder_token)
                    if not id_folder_token:
                        continue
                    
                    # 初始化变量
                    attachment_token = None
                    body_token = None
                    email_body = ""
                    
                    # 解析邮件内容
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            
                            # 处理PDF附件
                            if "attachment" in content_disposition:
                                filename = part.get_filename()
                                if filename and ATTACHMENT_PATTERN.match(filename):
                                    path = os.path.join(temp_dir, f"{base_name}.pdf")
                                    with open(path, 'wb') as f:
                                        f.write(part.get_payload(decode=True))
                                    
                                    # 上传附件获取file_token
                                    attachment_token = feishu_robot.upload_file(path, id_folder_token)
                                    if os.path.exists(path):
                                        os.remove(path)
                            
                            # 提取邮件正文
                            elif content_type == "text/plain" and "attachment" not in content_disposition:
                                try:
                                    body_content = part.get_payload(decode=True)
                                    if body_content:
                                        email_body += body_content.decode('utf-8', errors='ignore')
                                except Exception as e:
                                    logging.warning(f"解析邮件正文失败: {e}")
                    else:
                        # 非多部分邮件，直接获取正文
                        try:
                            email_body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except Exception as e:
                            logging.warning(f"解析邮件正文失败: {e}")
                    
                    # 处理邮件正文PDF
                    if attachment_token and email_body.strip():
                        path = os.path.join(temp_dir, f"{base_name}_body.pdf")
                        if save_text_as_pdf(email_body, path):
                            # 上传邮件正文PDF获取file_token
                            body_token = feishu_robot.upload_file(path, id_folder_token)
                            if os.path.exists(path):
                                os.remove(path)
                    
                    # 构建多维表格记录
                    if attachment_token:
                        new_record = {
                            "CN_NO": memo_id,
                            "AP_Credit_Note": [{"file_token": attachment_token}],  # 附件字段格式
                            "Email": [{"file_token": body_token}] if body_token else []  # 可选的邮件正文
                        }
                        records.append(new_record)
                        
                except Exception as e:
                    logging.error(f"处理邮件出错: {e}")
                    continue
        
        mail.logout()
        
        # 清理临时目录
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        return records
        
    except Exception as e:
        logging.error(f"主流程出错: {e}")
        # 清理临时目录
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        return []


def main():
    """主函数"""
    setup_logging(BASE_SAVE_DIR)
    logging.info("============ 任务开始 ============")
    
    # 改进字体文件检查
    if not os.path.exists(FONT_PATH):
        logging.warning("字体文件不存在，将跳过邮件正文PDF生成")
        # 不要直接返回，继续执行其他功能

    # 初始化飞书机器人
    robot = FeishuApplication(FEISHU_APP_ID, FEISHU_APP_SECRET)
    if not robot._token:
        logging.critical("无法获取Token")
        return

    # 创建日度文件夹
    daily_token, url = robot.create_folder(
        datetime.now().strftime("%Y-%m-%d"),
        FEISHU_PARENT_NODE
    )
    if not daily_token:
        logging.critical("无法创建日度文件夹")
        return
    
    logging.info(f"日度文件夹已就绪: {url}")
    
    # 处理邮件并收集记录
    records_to_write = process_and_upload_emails(robot, daily_token)

    # 写入多维表格
    if records_to_write:
        logging.info(f"准备将 {len(records_to_write)} 条记录写入多维表格...")
        success = robot.write_records_to_bitable(
            FEISHU_BITABLE_APP_TOKEN,
            FEISHU_BITABLE_TABLE_ID,
            records_to_write
        )
        
        if success:
            logging.info("✅ 多维表格写入成功")
        else:
            logging.error("❌ 多维表格写入失败，请检查配置参数")
            # 输出收集到的数据作为备用
            logging.info("📋 收集到的数据如下：")
            for i, record in enumerate(records_to_write, 1):
                logging.info(f"  记录 {i}: CN_NO={record['CN_NO']}, 附件已上传")
    else:
        logging.info("未生成任何有效记录")
    
    logging.info("============ 任务执行完毕 ============\n")


if __name__ == "__main__":
    main()
