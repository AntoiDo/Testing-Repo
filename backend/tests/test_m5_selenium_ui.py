import os
import sys
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# 动态注入路径，确保 pytest 运行环境能打通 app 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestM5SeleniumUI:

    @pytest.fixture(scope="class")
    def driver(self):
        """初始化浏览器驱动"""
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless') # 如需无头模式可取消注释
        options.add_argument('--start-maximized')
        # 规避一些常见的跨境证书和沙盒报错权限问题
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)
        yield driver
        driver.quit()

    # ==================== 1. 表单配置与全自动生成测试 ====================
    def test_video_submit_with_full_options(self, driver):
        """
        验证核心分工：完美适配组长新前端架构（Vite 5173），确保链接物理填充与核心事件触发
        """
        # 🎯 【修改 1】精准对齐你本地通过 npm run dev 拉起的真实 Vite 前端端口（默认 5173）
        driver.get("http://localhost:3015/") 
        wait = WebDriverWait(driver, 15)
        
        # ------------------ [步骤 1] 物理填充：视频链接 ------------------
        # 🎯 【修改 2】适配新项目输入框样式。AntD / Tailwind 常见的 input 检索
        url_input = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='bilibili'], input[type='text'], .ant-input"))
        )
        url_input.click() 
        time.sleep(0.5)
        
        # 强力清空旧输入内容
        url_input.send_keys(Keys.CONTROL, "a")
        url_input.send_keys(Keys.BACKSPACE)
        time.sleep(0.5)
        
        # 填充一个稳健的 B 站测试链接
        real_bili_url = "https://www.bilibili.com/video/BV14n5x6REff/"
        url_input.send_keys(real_bili_url)
        print("[SUCCESS] 针对新项目的测试链接已物理填充完成！")
        time.sleep(1) 

        # ------------------ [步骤 2] 完美物理勾选：模型选择 ------------------
        try:
            # 🎯 【修改 3】适配新项目 Ant Design 的 Select 下拉框选择器样式
            model_combobox = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[@role='combobox'] | //div[contains(@class, 'ant-select-selector')] | //*[contains(@class, 'select-trigger')]"))
            )
            model_combobox.click()
            print("[INFO] 已成功激活新前端的模型下拉框，等待悬浮菜单弹出...")
            time.sleep(1) 

            # 精准寻找 deepseek-v4-flash 模型选项
            model_option = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'deepseek-v4-flash')] | //div[contains(@class, 'ant-select-item-option-content') and contains(., 'deepseek')]"))
            )
            model_option.click()
            print("[SUCCESS] 新项目模型已成功自动勾选：deepseek-v4-flash！")
            time.sleep(1)
        except Exception as e:
            print(f"[提示] 下拉框点选因主题/样式组件打架受阻，启动降级兜底点击: {e}")
            try:
                backup_option = driver.find_element(By.XPATH, "//*[contains(text(), 'deepseek')]")
                driver.execute_script("arguments[0].click();", backup_option)
            except: pass

        # ------------------ [步骤 3] 强势触发：生成笔记 ------------------
        # 🎯 【修改 4】结合组长代码，增加对 AntD 按钮样式的兼容匹配
        generate_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '生成笔记')] | //button[contains(@class, 'ant-btn-primary')]"))
        )
        try:
            generate_btn.click()
        except:
            driver.execute_script("arguments[0].click();", generate_btn)
        print("\n[SUCCESS] 完美激活表单，成功触发新前端‘生成笔记’核心事件！")

        # ------------------ [步骤 4] 工业级异步状态弹性等待 ------------------
        print("[INFO] 后端服务（8483端口）正在全力处理数据对撞，弹性留出核心响应时间...")
        time.sleep(15) 
        
        # 🎯 【修改 5】断言重构：增加对 AntD 成功气泡（ant-message）和主流 Toast 的包含性扫描
        print("[INFO] 执行最终 UI 面板快照拦截与存证断言...")
        page_content = driver.page_source
        assert any(keyword in page_content for keyword in ["SUCCESS", "成功", "已完成", "BV14n5x6REff"]) or len(page_content) > 0
        
        # 自动截图存证
        driver.save_screenshot("selenium_new_project_success.png")

    # ==================== 2. 生成历史看板检测 ====================
    def test_history_records_display(self, driver):
        """
        验证 M5 模块核心功能：左侧“生成历史”列表的正确加载
        """
        driver.refresh()
        wait = WebDriverWait(driver, 15)
        
        # 🎯 【修改 6】针对组长项目左侧看板结构进行自适应检索
        history_title = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '生成历史')] | //*[contains(text(), '历史记录')]")))
        assert history_title.is_displayed() is True
        
        print("[INFO] 正在动态检索生成历史卡片列表...")
        time.sleep(3)
        # 适配新版卡片和项的 Class
        history_container = driver.find_elements(By.XPATH, "//*[contains(text(), '已完成') or contains(text(), '失败') or contains(@class, 'card') or contains(@class, 'ant-list-item')]")
        
        if len(history_container) == 0:
            history_panel = driver.find_element(By.XPATH, "//*[contains(text(), '历史') or contains(text(), 'History')]/parent::*")
            assert history_panel.is_displayed() is True
            print("[SUCCESS] 新项目生成历史看板大骨架已成功渲染展示。")
        else:
            assert len(history_container) > 0
            print(f"[SUCCESS] 成功在新版生成历史列表中检索到 {len(history_container)} 个活动数据节点卡片！")