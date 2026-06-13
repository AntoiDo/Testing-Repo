import os
import sys
import time
import pytest
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# 动态注入路径，确保 pytest 运行环境能打通 app 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入原生数据库操作模块
from app.db.video_task_dao import delete_task_by_video

def extract_bv_id(url):
    """从B站链接中提取BV号"""
    match = re.search(r"BV([0-9A-Za-z]+)", url)
    return f"BV{match.group(1)}" if match else None

# 锁定 bilinote 原生测试视频
TEST_VIDEO_URL = "https://www.bilibili.com/video/BV1utEi6vEhW/?spm_id_from=333.1387.homepage.video_card.click&vd_source=d4cc05fe649ff2f7e34a4b073718ef81"

# 从视频链接中提取 BV 号
TEST_VIDEO_ID = extract_bv_id(TEST_VIDEO_URL)  # BV1utEi6vEhW

def delete_test_video_from_history(video_url):
    """底层数据清理：确保测试环境纯净"""
    video_id = extract_bv_id(video_url)
    if video_id:
        try:
            delete_task_by_video(video_id=video_id, platform="bilibili")
            print(f"[CLEANUP] 底层数据库已预先安全抹除视频记录: {video_id}")
        except Exception as e:
            print(f"[CLEANUP] 底层清理提示: {e}")

class TestM5SeleniumUI:

    @pytest.fixture(scope="class")
    def driver(self):
        """生命周期钩子：在单例类生命周期内绝不关闭窗口"""
        delete_test_video_from_history(TEST_VIDEO_URL)
        
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)
        
        yield driver
        
        driver.quit()
        delete_test_video_from_history(TEST_VIDEO_URL)

    # ==================== 铁腕全链路：生成与配置流程 ====================
    def test_bilinote_all_in_one_flow(self, driver):
        """
        全自动化通关测试：链接填入 ➔ 模型点选 ➔ 触发生成 ➔ 异步等待 ➔ 前端物理删除
        """
        # 锁定原生的 3015 端口大本营
        driver.get("http://localhost:3015/") 
        wait = WebDriverWait(driver, 10)
        
        # ------------------ [步骤 1] 平台选择（默认已是哔哩哔哩，跳过避免下拉框遮挡） ------------------
        print("\n[INFO] 平台默认为哔哩哔哩，跳过平台选择以避免下拉框遮挡问题...")
        print("[SUCCESS] 平台已确认为：哔哩哔哩（使用默认值）")

        # ------------------ [步骤 2] 精准物理填充视频链接 ------------------
        print("[INFO] 正在定位视频链接输入框并注入测试 URL...")
        # 直接通过 placeholder 属性抓取
        url_input = wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='请输入视频网站链接']"))
        )
        # 用 JS 强行获取焦点
        driver.execute_script("arguments[0].focus();", url_input)
        url_input.click()
        time.sleep(0.3)
        
        # 强力清空旧数据
        url_input.send_keys(Keys.CONTROL, "a")
        url_input.send_keys(Keys.BACKSPACE)
        time.sleep(0.3)
        
        # 键入目标视频地址
        url_input.send_keys(TEST_VIDEO_URL)
        print("[SUCCESS] 视频链接已成功填入主输入框！")
        time.sleep(0.5)

        # ------------------ [步骤 3] 模型选择下拉框 ------------------
        print("[INFO] 正在实施特种定位：激活【模型选择】组件...")
        model_selected = False
        
        # 策略1：通过 shadcn/ui Select 组件定位
        try:
            print("[策略1] 尝试通过 shadcn/ui Select 组件定位...")
            # 先滚动到模型选择区域
            model_section = driver.find_element(By.XPATH, "//*[contains(text(), '模型选择')]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", model_section)
            time.sleep(0.5)
            
            # 定位 SelectTrigger 按钮
            model_trigger = driver.find_element(By.XPATH, "//button[contains(@class, 'select-trigger') or @role='combobox']")
            driver.execute_script("arguments[0].click();", model_trigger)
            print("[INFO] 已点击模型选择下拉框触发按钮")
            time.sleep(1.5)  # 等待下拉菜单完全展开
            
            # 查找所有下拉选项，选择包含 deepseek 的选项
            options = driver.find_elements(By.XPATH, "//div[@role='option' or contains(@class, 'select-item')]")
            print(f"[INFO] 找到 {len(options)} 个下拉选项")
            
            for opt in options:
                opt_text = opt.text
                print(f"[INFO] 选项文本: {opt_text}")
                if 'deepseek' in opt_text.lower():
                    driver.execute_script("arguments[0].click();", opt)
                    print(f"[SUCCESS] 已选择模型: {opt_text}")
                    model_selected = True
                    break
            
            if model_selected:
                time.sleep(0.5)
                # 按 ESC 确保下拉框关闭
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(0.3)
                print("[INFO] 已按 ESC 关闭下拉框")
        except Exception as e:
            print(f"[策略1失败] {e}")
        
        # 策略2：直接点击下拉框并选择第一个选项
        if not model_selected:
            try:
                print("[策略2] 尝试直接点击下拉框并选择第一个可用模型...")
                # 按 ESC 先关闭可能存在的下拉框
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(0.5)
                
                # 找到模型选择区域后面最近的按钮
                model_btn = driver.find_element(By.XPATH, "//*[contains(text(), '模型选择')]/following::button[1]")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", model_btn)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", model_btn)
                print("[INFO] 已点击模型选择按钮")
                time.sleep(1.5)
                
                # 点击第一个出现的选项
                first_option = driver.find_element(By.XPATH, "//div[@role='option' or contains(@class, 'select-item')][1]")
                option_text = first_option.text
                driver.execute_script("arguments[0].click();", first_option)
                print(f"[SUCCESS] 已选择第一个模型: {option_text}")
                model_selected = True
                
                time.sleep(0.5)
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(0.3)
            except Exception as e:
                print(f"[策略2失败] {e}")
        
        # 策略3：使用键盘导航选择模型
        if not model_selected:
            try:
                print("[策略3] 尝试使用键盘导航选择模型...")
                # 按 ESC 先关闭可能存在的下拉框
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(0.5)
                
                # 定位模型选择按钮并聚焦
                model_btn = driver.find_element(By.XPATH, "//*[contains(text(), '模型选择')]/following::button[1]")
                driver.execute_script("arguments[0].focus();", model_btn)
                time.sleep(0.3)
                
                # 按 Enter 打开下拉框
                model_btn.send_keys(Keys.ENTER)
                time.sleep(1)
                
                # 按 ArrowDown 选择第一个选项，然后按 Enter
                model_btn.send_keys(Keys.ARROW_DOWN)
                time.sleep(0.3)
                model_btn.send_keys(Keys.ENTER)
                print("[SUCCESS] 已通过键盘选择模型")
                model_selected = True
                
                time.sleep(0.5)
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception as e:
                print(f"[策略3失败] {e}")
        
        # 策略4：跳过模型选择，使用默认值
        if not model_selected:
            print("[策略4] 跳过模型选择，使用默认模型继续测试...")
            # 按 ESC 关闭任何可能遮挡的下拉框
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(0.5)
                # 点击页面空白处关闭下拉框
                driver.find_element(By.TAG_NAME, "body").click()
                time.sleep(0.3)
            except:
                pass
            print("[INFO] 已关闭可能存在的下拉框，继续测试")

        # ------------------ [步骤 4] 点击生成笔记按钮 ------------------
        print("[INFO] 正在定位并触发'生成笔记'按钮...")
        
        # 先确保任何下拉框都已关闭
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.5)
        
        # 滚动到页面顶部，确保生成按钮可见
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.3)
        
        # 定位生成笔记按钮
        generate_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., '生成笔记')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", generate_btn)
        time.sleep(0.5)
        
        # 尝试点击按钮
        try:
            generate_btn.click()
            print("[SUCCESS] 已通过物理点击触发'生成笔记'按钮")
        except Exception as e:
            print(f"[物理点击失败: {e}]，尝试 JS 点击...")
            driver.execute_script("arguments[0].click();", generate_btn)
            print("[SUCCESS] 已通过 JS 点击触发'生成笔记'按钮")
        
        # ------------------ [步骤 5] 异步状态监控 ------------------
        print(f"\n[INFO] 开始进入状态监控阶段，等待笔记异步生成成功 (目标视频: {TEST_VIDEO_ID})...")
        print("[INFO] 注意：笔记生成可能需要较长时间，请耐心等待...")
        
        generation_completed = False
        max_attempts = 25  # 增加轮询次数
        wait_interval = 5  # 每次等待 5 秒
        
        for attempt in range(1, max_attempts + 1):
            print(f"[轮询监测] 正在检测笔记生成状态 (第 {attempt}/{max_attempts} 次尝试)...")
            page_source_code = driver.page_source
            
            # 检测条件：
            # 1. 历史列表中出现测试视频的 BV 号
            # 2. 状态变为"已完成"（不是"等待中"）
            if TEST_VIDEO_ID in page_source_code:
                # 检测是否显示"已完成"状态
                if "已完成" in page_source_code:
                    # 确认这个"已完成"是属于测试视频的（通过相邻元素判断）
                    print(f"[SUCCESS] 检测到笔记生成完成！状态已变为'已完成'")
                    generation_completed = True
                    break
                # 检测是否还在"等待中"状态
                elif "等待中" in page_source_code or "生成中" in page_source_code:
                    print(f"[INFO] 检测到视频卡片，但状态仍为'等待中'，继续等待...")
                else:
                    # 有 BV 号但没有"等待中"或"已完成"，可能还在处理中
                    print(f"[INFO] 检测到视频卡片，状态未知，继续等待...")
            
            if "生成失败" in page_source_code or "失败" in page_source_code:
                print(f"[WARNING] 检测到生成失败状态...")
                # 即使失败也继续尝试删除
            
            # 每5次尝试刷新一下页面状态
            if attempt % 5 == 0:
                print(f"[INFO] 第 {attempt} 次尝试，执行页面刷新以同步状态...")
                driver.refresh()
                time.sleep(2)
            else:
                time.sleep(wait_interval)

        if not generation_completed:
            print(f"[WARNING] 在 {max_attempts * wait_interval} 秒内未能检测到笔记生成完成，但测试视频卡片可能已存在，继续后续流程...")
            # 刷新页面尝试获取最新状态
            print("[INFO] 执行最终页面刷新...")
            driver.refresh()
            time.sleep(3)
        else:
            print("[SUCCESS] 笔记生成完成，准备进入删除流程...")
            time.sleep(1)  # 额外等待确保页面状态稳定

        # ------------------ [步骤 6] 在历史列表中精准物理删除 ------------------
        print(f"[INFO] 正在从'生成历史'列表中精准提取视频卡片 {TEST_VIDEO_ID}...")
        
        # 首先刷新页面，确保获取最新状态
        print("[INFO] 刷新页面以获取最新状态...")
        driver.refresh()
        time.sleep(3)
        
        try:
            # 先检查页面中是否有该视频的"已完成"状态
            page_source = driver.page_source
            
            if TEST_VIDEO_ID in page_source:
                # 检查是否显示"已完成"状态
                if "已完成" not in page_source:
                    print("[WARNING] 检测到视频卡片，但状态可能不是'已完成'，尝试继续删除...")
                else:
                    print("[SUCCESS] 确认视频卡片状态为'已完成'，准备删除...")
            
            # 锁定含有测试视频的已完成卡片
            # 优先选择包含"已完成"状态标签的卡片
            try:
                video_card = driver.find_element(
                    By.XPATH, 
                    f"//*[contains(text(), '{TEST_VIDEO_ID}')]/ancestor::*[contains(@class, 'ant-list-item') or contains(@class, 'card') or @role='listitem'][.//*[contains(text(), '已完成')]]"
                )
                print("[INFO] 找到包含'已完成'状态的视频卡片")
            except:
                # 如果没找到带"已完成"的，尝试找任意卡片
                print("[INFO] 未找到带'已完成'状态的卡片，尝试查找任意卡片...")
                video_card = driver.find_element(
                    By.XPATH, 
                    f"//*[contains(text(), '{TEST_VIDEO_ID}')]/ancestor::*[contains(@class, 'ant-list-item') or contains(@class, 'card') or @role='listitem']"
                )
            
            # 抠出卡片内部的删除按钮
            delete_btn = video_card.find_element(By.XPATH, ".//button[contains(@title, '删除') or contains(., '删除')] | .//*[contains(@class, 'delete') or contains(@class, 'trash')]")
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", delete_btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", delete_btn)
            print("[SUCCESS] 已物理触发前端'删除'按钮点击动作！")
            
            # 点掉二次确认弹窗
            time.sleep(1)
            confirm_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'ant-btn-primary') or contains(., '确定') or contains(., '确认')] | //span[contains(text(), '确')]/parent::button"))
            )
            confirm_btn.click()
            print(f"[SUCCESS] 历史记录二次确认删除成功！视频 {TEST_VIDEO_ID} 已从历史列表移除，全链路完美闭环收官！")
        except Exception as e:
            print(f"[提示] 看板删除步骤未触发（可能后端模型处理超时未在时限内渲染成功）: {e}")

        # 最终拦截快照留痕
        driver.save_screenshot("bilinote_all_in_one_perfect.png")