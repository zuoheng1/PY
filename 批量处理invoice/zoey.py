import os
import re
import imaplib
import email
from datetime import datetime, timedelta
import logging
import requests
from fpdf import FPDF
import shutil
from dotenv import load_dotenv
from typing import List, Optional

# 加载 .env 文件
load_dotenv()


class Config:
    """配置管理类 - 统一管理所有环境变量"""
    
    def __init__(self):
        # 邮件配置
        self.IMAP_URL: str = self._get_env('IMAP_URL', 'imap.gmail.com')
        self.EMAIL_USER: str = self._get_env('EMAIL_USER', required=True)
        self.EMAIL_PASS: str = self._get_env('EMAIL_PASS', required=True)
        self.VALID_SENDERS: List[str] = self._get_env(
            'VALID_SENDERS', 
            'Donna.Villani@directed.com.au'
        ).split(',')
        
        # 邮件处理配置
        self.ATTACHMENT_PATTERN = re.compile(r'^AP Credit Memo.*\.pdf$', re.IGNORECASE)
        self.EMAIL_START_DATE: str = self._get_env('EMAIL_START_DATE', '11-Jul-2025')
        self.EMAIL_SENT_DATE: str = self._get_env('EMAIL_SENT_DATE', '15-Jul-2025')
        
        # 文件系统配置
        self.BASE_SAVE_DIR: str = self._get_env(
            'BASE_SAVE_DIR', 
            os.path.expanduser('~/Desktop/CN发票下载')
        )
        self.FONT_PATH: str = self._get_env(
            'FONT_PATH', 
            '/System/Library/Fonts/STHeiti Medium.ttc'
        )
        
        # 飞书配置
        self.FEISHU_APP_ID: str = self._get_env('FEISHU_APP_ID', required=True)
        self.FEISHU_APP_SECRET: str = self._get_env('FEISHU_APP_SECRET', required=True)
        self.FEISHU_PARENT_NODE: str = self._get_env('FEISHU_PARENT_NODE', required=True)
        self.FEISHU_BITABLE_APP_TOKEN: str = self._get_env('FEISHU_BITABLE_APP_TOKEN', required=True)
        self.FEISHU_BITABLE_TABLE_ID: str = self._get_env('FEISHU_BITABLE_TABLE_ID', required=True)
        
        # 验证所有必需的环境变量
        self._validate_config()
    
    def _get_env(self, key: str, default: Optional[str] = None, required: bool = False) -> str:
        """获取环境变量的统一方法"""
        value = os.getenv(key, default)
        if required and not value:
            raise ValueError(f'必需的环境变量 {key} 未设置')
        return value or ''
    
    def _validate_config(self) -> None:
        """验证配置的完整性"""
        required_fields = [
            'EMAIL_USER', 'EMAIL_PASS', 'FEISHU_APP_ID', 'FEISHU_APP_SECRET',
            'FEISHU_PARENT_NODE', 'FEISHU_BITABLE_APP_TOKEN', 'FEISHU_BITABLE_TABLE_ID'
        ]
        
        missing_vars = []
        for field in required_fields:
            if not getattr(self, field, None):
                missing_vars.append(field)
        
        if missing_vars:
            raise ValueError(f'以下必需的环境变量未设置: {", ".join(missing_vars)}')
        
        logging.info("配置验证通过")


# 全局配置实例
config = Config()


def setup_logging(log_base_dir: str) -> None:
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
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = self.get_tenant_access_token()
        self.headers = {'Authorization': f'Bearer {self._token}'} if self._token else {}

    def get_tenant_access_token(self) -> Optional[str]:
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
                return data['tenant_access_token']
            else:
                logging.error(f'获取token失败：{response.text}')
                return None
        except Exception as e:
            logging.error(f"请求Token出错: {e}")
            return None

    def create_folder(self, name: str, parent: str) -> tuple[Optional[str], Optional[str]]:
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
                logging.error(f'创建文件夹失败：{response.text}')
                return None, None
        except Exception as e:
            logging.error(f"创建文件夹出错: {e}")
            return None, None

    def upload_file(self, path: str, parent: str) -> Optional[str]:
        """上传文件到云空间"""
        if not self._token or not os.path.isfile(path):
            return None
        
        url = 'https://open.feishu.cn/open-apis/drive/v1/files/upload_all'
        
        try:
            name = os.path.basename(path)
            file_size = os.path.getsize(path)
            
            with open(path, 'rb') as file:
                files = {
                    'file_name': (None, name),
                    'parent_type': (None, 'bitable_file'),
                    'parent_node': (None, config.FEISHU_BITABLE_APP_TOKEN),
                    'size': (None, str(file_size)),
                    'file': (name, file, 'application/pdf')
                }
                
                headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
                response = requests.post(url, headers=headers, files=files)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 0:
                    return data['data']['file_token']
                else:
                    logging.error(f"文件上传失败：{response.text}")
                    return None
                    
        except Exception as e:
            logging.error(f"上传文件出错: {e}")
            return None

    def write_records_to_bitable(self, app_token: str, table_id: str, records: List[dict]) -> bool:
        """写入记录到多维表格"""
        if not self._token or not records:
            return False
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
        payload = {"records": [{"fields": r} for r in records]}
        
        try:
            response = requests.post(
                url,
                headers={**self.headers, 'Content-Type': 'application/json'},
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    logging.info(f"成功写入 {len(records)} 条记录")
                    return True
                else:
                    logging.error(f"API返回错误: {data.get('msg', '未知错误')}")
                    return False
            else:
                logging.error(f"写入HTTP错误: {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"写入异常: {str(e)}")
            return False


def save_text_as_pdf(text: str, path: str) -> bool:
    """将文本保存为PDF"""
    try:
        pdf = FPDF()
        pdf.add_page()
        
        try:
            if os.path.exists(config.FONT_PATH):
                pdf.add_font('Heiti', '', config.FONT_PATH, uni=True)
                pdf.set_font('Heiti', size=12)
            else:
                pdf.set_font('Arial', size=12)
                text = text.encode('ascii', 'ignore').decode('ascii')
        except Exception:
            pdf.set_font('Arial', size=12)
            text = text.encode('ascii', 'ignore').decode('ascii')
        
        pdf.multi_cell(0, 10, txt=text)
        pdf.output(path)
        return True
    except Exception as e:
        logging.error(f"创建PDF失败: {e}")
        return False


def process_and_upload_emails(feishu_robot: FeishuApplication, daily_folder_token: str) -> List[dict]:
    """处理和上传邮件"""
    records = []
    temp_dir = os.path.join(config.BASE_SAVE_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        mail = imaplib.IMAP4_SSL(config.IMAP_URL)
        mail.login(config.EMAIL_USER, config.EMAIL_PASS)
        mail.select('Inbox')
        
        for sender in config.VALID_SENDERS:
            # 修改搜索条件以包含起止日期
            # 使用 ON 或组合条件来包含边界日期
            search_criteria = f'(FROM "{sender}" SINCE "{config.EMAIL_START_DATE}" ON "{config.EMAIL_SENT_DATE}")'
            # 如果起止日期相同，只使用 ON
            if config.EMAIL_START_DATE == config.EMAIL_SENT_DATE:
                search_criteria = f'(FROM "{sender}" ON "{config.EMAIL_START_DATE}")'
            # 如果需要日期范围，使用 SINCE 起始日期，但不使用 BEFORE 结束日期
            else:
                # 计算结束日期的下一天用于 BEFORE 条件
                try:
                    end_date = datetime.strptime(config.EMAIL_SENT_DATE, '%d-%b-%Y')
                    next_day = end_date + timedelta(days=1)
                    next_day_str = next_day.strftime('%d-%b-%Y')
                    search_criteria = f'(FROM "{sender}" SINCE "{config.EMAIL_START_DATE}" BEFORE "{next_day_str}")'
                except ValueError:
                    # 如果日期格式解析失败，回退到原始逻辑
                    search_criteria = f'(FROM "{sender}" SINCE "{config.EMAIL_START_DATE}" BEFORE "{config.EMAIL_SENT_DATE}")'
            
            _, data = mail.search(None, search_criteria)
            
            for mail_id in data[0].split():
                try:
                    _, msg_data = mail.fetch(mail_id, '(RFC822)')
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    attachment_token = None
                    body_token = None
                    email_body = ""
                    memo_id = None
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            
                            if "attachment" in content_disposition:
                                filename = part.get_filename()
                                if filename and config.ATTACHMENT_PATTERN.match(filename):
                                    match = re.search(r'Credit Memo[_\s]*([\d]+)', filename, re.IGNORECASE)
                                    if match:
                                        memo_id = match.group(1)
                                        base_name = f"Credit Memo_{memo_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                        
                                        id_folder_token, _ = feishu_robot.create_folder(memo_id, daily_folder_token)
                                        if id_folder_token:
                                            path = os.path.join(temp_dir, f"{base_name}.pdf")
                                            with open(path, 'wb') as f:
                                                f.write(part.get_payload(decode=True))
                                            
                                            attachment_token = feishu_robot.upload_file(path, id_folder_token)
                                            if os.path.exists(path):
                                                os.remove(path)
                            
                            elif content_type == "text/plain" and "attachment" not in content_disposition:
                                try:
                                    body_content = part.get_payload(decode=True)
                                    if body_content:
                                        email_body += body_content.decode('utf-8', errors='ignore')
                                except Exception:
                                    pass
                    else:
                        try:
                            email_body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except Exception:
                            pass
                    
                    if not memo_id or not attachment_token:
                        continue
                    
                    if attachment_token and email_body.strip():
                        base_name = f"Credit Memo_{memo_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        path = os.path.join(temp_dir, f"{base_name}_body.pdf")
                        if save_text_as_pdf(email_body, path):
                            id_folder_token, _ = feishu_robot.create_folder(memo_id, daily_folder_token)
                            if id_folder_token:
                                body_token = feishu_robot.upload_file(path, id_folder_token)
                            if os.path.exists(path):
                                os.remove(path)
                    
                    if attachment_token and memo_id:
                        new_record = {
                            "CN_NO": memo_id,
                            "AP_Credit_Note": [{"file_token": attachment_token}],
                            "Email": [{"file_token": body_token}] if body_token else []
                        }
                        records.append(new_record)
                        
                except Exception as e:
                    logging.error(f"处理邮件出错: {e}")
                    continue
        
        mail.logout()
        
    except Exception as e:
        logging.error(f"主流程出错: {e}")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    return records


def main() -> None:
    """主函数"""
    setup_logging(config.BASE_SAVE_DIR)
    logging.info("任务开始")
    
    robot = FeishuApplication(config.FEISHU_APP_ID, config.FEISHU_APP_SECRET)
    if not robot._token:
        logging.critical("无法获取Token")
        return

    daily_token, _ = robot.create_folder(
        datetime.now().strftime("%Y-%m-%d"),
        config.FEISHU_PARENT_NODE
    )
    if not daily_token:
        logging.critical("无法创建日度文件夹")
        return
    
    records_to_write = process_and_upload_emails(robot, daily_token)

    if records_to_write:
        success = robot.write_records_to_bitable(
            config.FEISHU_BITABLE_APP_TOKEN,
            config.FEISHU_BITABLE_TABLE_ID,
            records_to_write
        )
        
        if success:
            logging.info("多维表格写入成功")
        else:
            logging.error("多维表格写入失败")
    else:
        logging.info("未生成任何有效记录")
    
    logging.info("任务执行完毕")


if __name__ == "__main__":
    main()
