"""
PSI Automation Page Objects
- pages.server: PSI 관리자 웹 콘솔 Page Objects (Playwright)
- pages.client: PSI 보안점검 데스크톱 클라이언트 Page Objects (UIA)
  - pages.client.modals: 메인 화면 호출 모달/팝업
  - pages.client.tray: 트레이 연동 팝업/웹뷰
"""

import sys

# Server (관리자 웹 콘솔) Page Objects
from pages.server.base_page import AdminBasePage
from pages.server.manage_config_page import AdminManageConfigPage
from pages.server.patch_page import AdminPatchPage
from pages.server.pcsafe_manage_page import AdminPcsafeManagePage
from pages.server.pcsafe_page import AdminPcsafePage

# Client (데스크톱 클라이언트) Page Objects
from pages.client.main_page import MainPage
from pages.client.inspection_result_page import InspectionResultPage
from pages.client.modals.help_modal_page import (
    HelpModalPage,
    HELP_ITEMS_53_KO,
    HELP_ITEMS_53_EN,
)
from pages.client.modals.password_safety_modal_page import (
    PasswordSafetyModalPage,
    PASSWORD_CRITERIA_NAMES,
)
from pages.client.tray.tray_patch_status_page import TrayPatchStatusPage
from pages.client.tray.user_info_form_page import UserInfoFormPage

# 기존 레거시 import(from pages.main_page import MainPage 등) 완벽한 하위 호환성 매핑
import pages.server.base_page as _admin_base_page
import pages.server.manage_config_page as _admin_manage_config_page
import pages.server.patch_page as _admin_patch_page
import pages.server.pcsafe_manage_page as _admin_pcsafe_manage_page
import pages.server.pcsafe_page as _admin_pcsafe_page

import pages.client.main_page as _main_page
import pages.client.inspection_result_page as _inspection_result_page
import pages.client.modals.help_modal_page as _help_modal_page
import pages.client.modals.password_safety_modal_page as _password_safety_modal_page
import pages.client.tray.tray_patch_status_page as _tray_patch_status_page
import pages.client.tray.user_info_form_page as _user_info_form_page

sys.modules.setdefault("pages.admin_base_page", _admin_base_page)
sys.modules.setdefault("pages.admin_manage_config_page", _admin_manage_config_page)
sys.modules.setdefault("pages.admin_patch_page", _admin_patch_page)
sys.modules.setdefault("pages.admin_pcsafe_manage_page", _admin_pcsafe_manage_page)
sys.modules.setdefault("pages.admin_pcsafe_page", _admin_pcsafe_page)

sys.modules.setdefault("pages.main_page", _main_page)
sys.modules.setdefault("pages.inspection_result_page", _inspection_result_page)
sys.modules.setdefault("pages.help_modal_page", _help_modal_page)
sys.modules.setdefault("pages.password_safety_modal_page", _password_safety_modal_page)
sys.modules.setdefault("pages.tray_patch_status_page", _tray_patch_status_page)
sys.modules.setdefault("pages.user_info_form_page", _user_info_form_page)

__all__ = [
    # Server
    "AdminBasePage",
    "AdminManageConfigPage",
    "AdminPatchPage",
    "AdminPcsafeManagePage",
    "AdminPcsafePage",
    # Client
    "MainPage",
    "InspectionResultPage",
    "HelpModalPage",
    "HELP_ITEMS_53_KO",
    "HELP_ITEMS_53_EN",
    "PasswordSafetyModalPage",
    "PASSWORD_CRITERIA_NAMES",
    "TrayPatchStatusPage",
    "UserInfoFormPage",
]
